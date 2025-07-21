from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from ..models import Profile, Conversation, Message, MessageLimit, Report
from ..forms import MessageForm, ReportForm
from ..cache_utils import (
    get_cached_user_profile, get_cached_conversation_list, 
    cache_conversation_list, invalidate_conversation_cache,
    invalidate_unread_count_cache
)


@login_required
def conversations_list(request):
    """Список всех переписок пользователя с кэшированием"""
    try:
        own_profile = get_cached_user_profile(request.user)
    except Profile.DoesNotExist:
        messages.info(request, 'Сначала создайте свой профиль!')
        return redirect('profiles:create_profile')
    
    if not own_profile:
        messages.info(request, 'Сначала создайте свой профиль!')
        return redirect('profiles:create_profile')
    
    # Пытаемся получить кэшированные переписки
    cached_conversations = get_cached_conversation_list(request.user)
    
    if cached_conversations is not None:
        conversation_data = cached_conversations
    else:
        # Получаем все переписки пользователя
        conversations = Conversation.objects.filter(
            Q(participant1=request.user) | Q(participant2=request.user)
        ).prefetch_related('messages').order_by('-last_message_at')
        
        # Подготавливаем данные для каждой переписки
        conversation_data = []
        for conv in conversations:
            other_user = conv.get_other_participant(request.user)
            try:
                other_profile = get_cached_user_profile(other_user)
            except Profile.DoesNotExist:
                continue
            
            if not other_profile:
                continue
            
            # Последнее сообщение
            last_message = conv.messages.last()
            
            # Количество непрочитанных сообщений
            unread_count = conv.messages.filter(receiver=request.user, is_read=False).count()
            
            conversation_data.append({
                'conversation': conv,
                'other_user': other_user,
                'other_profile': other_profile,
                'last_message': last_message,
                'unread_count': unread_count
            })
        
        # Кэшируем список переписок
        cache_conversation_list(request.user, conversation_data, timeout=180)
    
    context = {
        'conversation_data': conversation_data,
    }
    
    return render(request, 'profiles/messages/conversations_list.html', context)


@login_required
def conversation_detail(request, conversation_id):
    """Детальная страница переписки"""
    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        messages.error(request, 'Переписка не найдена!')
        return redirect('profiles:conversations_list')
    
    # Проверяем что пользователь участвует в переписке
    if request.user not in [conversation.participant1, conversation.participant2]:
        messages.error(request, 'У вас нет доступа к этой переписке!')
        return redirect('profiles:conversations_list')
    
    # Получаем собеседника
    other_user = conversation.get_other_participant(request.user)
    try:
        other_profile = get_cached_user_profile(other_user)
    except Profile.DoesNotExist:
        messages.error(request, 'Профиль собеседника не найден!')
        return redirect('profiles:conversations_list')
    
    if not other_profile:
        messages.error(request, 'Профиль собеседника не найден!')
        return redirect('profiles:conversations_list')
    
    # Получаем все сообщения в переписке с оптимизированным запросом
    messages_qs = Message.objects.in_conversation(conversation).order_by('sent_at')
    
    # Отмечаем все непрочитанные сообщения пользователя как прочитанные (до пагинации)
    unread_messages = Message.objects.unread_for_user(request.user).filter(conversation=conversation)
    for msg in unread_messages:
        msg.mark_as_read()
    
    # Инвалидируем кэш количества непрочитанных сообщений
    if unread_messages.exists():
        invalidate_unread_count_cache(request.user)
    
    # Применяем пагинацию к сообщениям (20 сообщений на страницу)
    paginator = Paginator(messages_qs, 20)
    page_number = request.GET.get('page', 1)
    
    try:
        messages_page = paginator.get_page(page_number)
    except PageNotAnInteger:
        messages_page = paginator.get_page(1)
    except EmptyPage:
        messages_page = paginator.get_page(paginator.num_pages)
    
    # Обработка формы отправки сообщения
    message_form = MessageForm()
    if request.method == 'POST':
        if 'send_message' in request.POST:
            message_form = MessageForm(request.POST)
            if message_form.is_valid():
                # Проверяем лимиты антиспам
                can_send, error_msg = check_message_limits(request.user, other_user)
                if can_send:
                    # Создаем сообщение
                    Message.objects.create(
                        conversation=conversation,
                        sender=request.user,
                        receiver=other_user,
                        content=message_form.cleaned_data['content']
                    )
                    
                    # Обновляем время последнего сообщения в переписке
                    conversation.update_last_message_time()
                    
                    # Обновляем лимиты
                    update_message_limits(request.user, other_user)
                    
                    # Инвалидируем кэши переписок для обоих пользователей
                    invalidate_conversation_cache(request.user)
                    invalidate_conversation_cache(other_user)
                    invalidate_unread_count_cache(other_user)
                    
                    messages.success(request, 'Сообщение отправлено!')
                    return redirect('profiles:conversation_detail', conversation_id=conversation.id)
                else:
                    messages.error(request, error_msg)
    
    context = {
        'conversation': conversation,
        'other_profile': other_profile,
        'other_user': other_user,
        'messages_page': messages_page,
        'message_form': message_form,
    }
    
    return render(request, 'profiles/messages/conversation_detail.html', context)


@login_required
def start_conversation(request, user_id):
    """Начать новую переписку с пользователем"""
    try:
        other_user = User.objects.get(id=user_id)
        other_profile = Profile.objects.get(user=other_user)
    except (User.DoesNotExist, Profile.DoesNotExist):
        messages.error(request, 'Пользователь не найден!')
        return redirect('/')
    
    # Нельзя писать самому себе
    if other_user == request.user:
        messages.error(request, 'Нельзя написать самому себе!')
        return redirect('profiles:view_profile', profile_id=other_profile.id)
    
    # Проверяем лимиты
    can_send, error_msg = check_message_limits(request.user, other_user)
    if not can_send:
        messages.error(request, error_msg)
        return redirect('profiles:view_profile', profile_id=other_profile.id)
    
    # Ищем существующую переписку
    conversation = Conversation.objects.filter(
        Q(participant1=request.user, participant2=other_user) |
        Q(participant1=other_user, participant2=request.user)
    ).first()
    
    # Если переписки нет, создаем новую
    if not conversation:
        conversation = Conversation.objects.create(
            participant1=request.user,
            participant2=other_user
        )
    
    # Перенаправляем в переписку
    return redirect('profiles:conversation_detail', conversation_id=conversation.id)


@login_required
def report_user(request, user_id):
    """Подать жалобу на пользователя"""
    try:
        reported_user = User.objects.get(id=user_id)
        reported_profile = Profile.objects.get(user=reported_user)
    except (User.DoesNotExist, Profile.DoesNotExist):
        messages.error(request, 'Пользователь не найден!')
        return redirect('/')
    
    # Нельзя жаловаться на самого себя
    if reported_user == request.user:
        messages.error(request, 'Нельзя пожаловаться на самого себя!')
        return redirect('profiles:view_profile', profile_id=reported_profile.id)
    
    # Проверяем, не подавал ли пользователь уже жалобу
    existing_report = Report.objects.filter(
        reporter=request.user,
        reported_user=reported_user
    ).first()
    
    if existing_report:
        messages.info(request, 'Вы уже подали жалобу на этого пользователя.')
        return redirect('profiles:view_profile', profile_id=reported_profile.id)
    
    form = ReportForm()
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            Report.objects.create(
                reporter=request.user,
                reported_user=reported_user,
                reason=form.cleaned_data['reason'],
                description=form.cleaned_data['description']
            )
            messages.success(request, 'Жалоба подана и будет рассмотрена администрацией.')
            return redirect('profiles:view_profile', profile_id=reported_profile.id)
    
    context = {
        'reported_profile': reported_profile,
        'form': form,
    }
    
    return render(request, 'profiles/messages/report_form.html', context)


def check_message_limits(sender, receiver):
    """Проверить лимиты сообщений (антиспам)"""
    try:
        limit, created = MessageLimit.objects.get_or_create(
            sender=sender,
            receiver=receiver
        )
        
        if not limit.can_send_message():
            return False, 'Превышен лимит сообщений. Дождитесь ответа или попробуйте через час.'
        
        return True, None
    except Exception:
        return True, None


def update_message_limits(sender, receiver):
    """Обновить лимиты сообщений после отправки"""
    try:
        limit, created = MessageLimit.objects.get_or_create(
            sender=sender,
            receiver=receiver
        )
        limit.increment_unanswered()
        
        # Если получатель отправляет ответ, сбрасываем его лимит
        reverse_limit = MessageLimit.objects.filter(
            sender=receiver,
            receiver=sender
        ).first()
        if reverse_limit:
            reverse_limit.reset_unanswered()
    except Exception:
        pass
