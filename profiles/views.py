from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.core.management import call_command
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.utils import OperationalError
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
from django.conf import settings
from django import forms
import os

from .models import Profile, Photo, Conversation, Message, MessageLimit, Report
from .forms import ProfileForm, ProfileSearchForm, PhotoUploadForm, MultiplePhotoUploadForm, AdvancedProfileSearchForm, MessageForm, ReportForm
from .cache_utils import (
    get_cached_user_profile, invalidate_user_profile_cache,
    get_cached_profile_stats, get_cached_recent_profiles,
    cache_search_results_data, get_cached_search_results, invalidate_search_cache,
    get_cached_conversation_list, cache_conversation_list, invalidate_conversation_cache,
    get_cached_unread_count, cache_unread_count, invalidate_unread_count_cache,
    cache_profile, cache_search_results, cache_conversation_data,
    invalidate_all_profile_caches
)




# ====================== НОВЫЕ ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ ФОТОГРАФИЯМИ ======================

@login_required
def manage_photos(request):
    """Управление фотографиями профиля"""
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        messages.info(request, 'Сначала создайте профиль!')
        return redirect('profiles:create_profile')
    
    photos = profile.photos.all().order_by('-is_primary', '-uploaded_at')
    
    return render_photos_management(request, profile, photos)


@login_required
def upload_photo(request):
    """Загрузка одной фотографии"""
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        messages.error(request, 'Сначала создайте профиль!')
        return redirect('profiles:create_profile')
    
    if request.method == 'POST':
        form = PhotoUploadForm(request.POST, request.FILES, profile=profile)
        if form.is_valid():
            photo = form.save()
            messages.success(request, 'Фотография успешно загружена!')
            return redirect('profiles:manage_photos')
        else:
            messages.error(request, 'Ошибки при загрузке фотографии. Проверьте данные.')
    else:
        form = PhotoUploadForm(profile=profile)
    
    return render_photo_upload_form(request, form, 'Загрузка фотографии', single=True)


@login_required
def upload_multiple_photos(request):
    """Загрузка нескольких фотографий"""
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        messages.error(request, 'Сначала создайте профиль!')
        return redirect('profiles:create_profile')
    
    if request.method == 'POST':
        form = MultiplePhotoUploadForm(request.POST, request.FILES, profile=profile)
        if form.is_valid():
            files = form.cleaned_data['images']
            uploaded_count = 0
            
            for file in files:
                try:
                    photo = Photo.objects.create(
                        profile=profile,
                        image=file,
                        is_primary=(not profile.photos.exists()),  # Первая фото = основная
                        is_verified=True
                    )
                    uploaded_count += 1
                except Exception as e:
                    messages.warning(request, f'Не удалось загрузить файл "{file.name}": {str(e)}')
            
            if uploaded_count > 0:
                messages.success(request, f'Успешно загружено {uploaded_count} фотографий!')
            return redirect('profiles:manage_photos')
        else:
            messages.error(request, 'Ошибки при загрузке фотографий. Проверьте данные.')
    else:
        form = MultiplePhotoUploadForm(profile=profile)
    
    return render_photo_upload_form(request, form, 'Загрузка нескольких фотографий', single=False)


@login_required
def delete_photo(request, photo_id):
    """Удаление фотографии"""
    try:
        profile = Profile.objects.get(user=request.user)
        photo = get_object_or_404(Photo, id=photo_id, profile=profile)
        
        # Если удаляем основную фотографию, назначаем другую основной
        if photo.is_primary:
            other_photos = profile.photos.exclude(id=photo_id).first()
            if other_photos:
                other_photos.is_primary = True
                other_photos.save()
        
        photo.delete()
        messages.success(request, 'Фотография удалена!')
        
    except Profile.DoesNotExist:
        messages.error(request, 'Профиль не найден!')
    except Exception as e:
        messages.error(request, f'Ошибка при удалении фотографии: {str(e)}')
    
    return redirect('profiles:manage_photos')


@login_required
def set_primary_photo(request, photo_id):
    """Установка основной фотографии"""
    try:
        profile = Profile.objects.get(user=request.user)
        photo = get_object_or_404(Photo, id=photo_id, profile=profile)
        
        # Убираем флаг основной у всех фотографий
        profile.photos.update(is_primary=False)
        
        # Устанавливаем основной новую фотографию
        photo.is_primary = True
        photo.save()
        
        messages.success(request, 'Основная фотография изменена!')
        
    except Profile.DoesNotExist:
        messages.error(request, 'Профиль не найден!')
    except Exception as e:
        messages.error(request, f'Ошибка при изменении основной фотографии: {str(e)}')
    
    return redirect('profiles:manage_photos')


def render_photos_management(request, profile, photos):
    """Рендеринг страницы управления фотографиями"""
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Управление фотографиями - Сайт знакомств</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
            .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
            h1 {{ color: #333; text-align: center; margin-bottom: 30px; }}
            .actions {{ text-align: center; margin-bottom: 30px; }}
            .btn {{ padding: 12px 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; margin: 0 10px; text-decoration: none; display: inline-block; transition: transform 0.2s; }}
            .btn:hover {{ transform: translateY(-2px); }}
            .btn-success {{ background: #28a745; }}
            .btn-danger {{ background: #dc3545; }}
            .btn-secondary {{ background: #6c757d; }}
            .photos-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
            .photo-card {{ background: #f8f9fa; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.2s; }}
            .photo-card:hover {{ transform: translateY(-5px); }}
            .photo-image {{ width: 100%; height: 200px; object-fit: cover; }}
            .photo-info {{ padding: 15px; }}
            .photo-actions {{ display: flex; gap: 10px; margin-top: 10px; }}
            .photo-badge {{ background: #ffc107; color: #333; padding: 3px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }}
            .messages {{ margin-bottom: 20px; }}
            .message {{ padding: 12px; border-radius: 8px; margin-bottom: 10px; }}
            .message.success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .message.error {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
            .message.info {{ background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }}
            .message.warning {{ background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }}
            .no-photos {{ text-align: center; padding: 50px; color: #666; }}
            .stats {{ background: #e8f4fd; padding: 20px; border-radius: 8px; margin-bottom: 20px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📸 Управление фотографиями</h1>
            
            <div class="messages">
    """
    
    # Добавляем сообщения
    if messages.get_messages(request):
        for message in messages.get_messages(request):
            message_class = message.tags if message.tags else 'info'
            html += f'<div class="message {message_class}">{message}</div>'
    
    # Статистика
    photos_count = photos.count()
    primary_photo = photos.filter(is_primary=True).first()
    
    html += f"""
            </div>
            
            <div class="stats">
                <h3>📊 Статистика</h3>
                <p><strong>Всего фотографий:</strong> {photos_count}/10</p>
                <p><strong>Основная фотография:</strong> {'Установлена' if primary_photo else 'Не установлена'}</p>
            </div>
            
            <div class="actions">
                <a href="/profiles/photos/upload/" class="btn">📤 Загрузить фотографию</a>
                <a href="/profiles/photos/upload-multiple/" class="btn btn-success">📤📤 Загрузить несколько</a>
                <a href="/profiles/my/" class="btn btn-secondary">👤 Мой профиль</a>
                <a href="/" class="btn btn-secondary">🏠 Главная</a>
            </div>
    """
    
    if photos.exists():
        html += '<div class="photos-grid">'
        
        for photo in photos:
            try:
                photo_url = photo.image.url if photo.image else None
                upload_date = photo.uploaded_at.strftime('%d.%m.%Y')
                
                html += f"""
                    <div class="photo-card">
                        <img src="{photo_url}" alt="Фото профиля" class="photo-image" onerror="this.style.display='none';">
                        <div class="photo-info">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span>Загружено: {upload_date}</span>
                                {f'<span class="photo-badge">🌟 Основная</span>' if photo.is_primary else ''}
                            </div>
                            <div class="photo-actions">
                """
                
                # Кнопка "Сделать основной" только если это не основная фотография
                if not photo.is_primary:
                    html += f'<a href="/profiles/photos/set-primary/{photo.id}/" class="btn" style="padding: 6px 12px; font-size: 12px;">⭐ Сделать основной</a>'
                
                # Кнопка удаления
                html += f"""
                                <a href="/profiles/photos/delete/{photo.id}/" class="btn btn-danger" 
                                   style="padding: 6px 12px; font-size: 12px;"
                                   onclick="return confirm('Вы уверены, что хотите удалить эту фотографию?')">🗑️ Удалить</a>
                            </div>
                        </div>
                    </div>
                """
            except Exception:
                continue
        
        html += '</div>'
    else:
        html += """
            <div class="no-photos">
                <h3>📷 У вас пока нет фотографий</h3>
                <p>Загрузите свои первые фотографии, чтобы другие пользователи могли увидеть вас!</p>
            </div>
        """
    
    html += """
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html)


def render_photo_upload_form(request, form, title, single=True):
    """Рендеринг формы загрузки фотографий"""
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - Сайт знакомств</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
            h1 {{ color: #333; text-align: center; margin-bottom: 30px; }}
            .form-group {{ margin-bottom: 20px; }}
            .form-group label {{ display: block; margin-bottom: 8px; color: #333; font-weight: bold; }}
            .form-control {{ width: 100%; padding: 12px; border: 2px solid #e1e1e1; border-radius: 8px; font-size: 16px; transition: border-color 0.3s; box-sizing: border-box; }}
            .form-control:focus {{ border-color: #667eea; outline: none; }}
            .form-check {{ display: flex; align-items: center; margin-bottom: 10px; }}
            .form-check-input {{ margin-right: 10px; }}
            .btn {{ padding: 14px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: transform 0.2s; margin-right: 10px; }}
            .btn:hover {{ transform: translateY(-2px); }}
            .btn-secondary {{ background: #6c757d; }}
            .messages {{ margin-bottom: 20px; }}
            .message {{ padding: 12px; border-radius: 8px; margin-bottom: 10px; }}
            .message.success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .message.error {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
            .message.info {{ background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }}
            .errorlist {{ list-style: none; padding: 0; margin: 5px 0; }}
            .errorlist li {{ color: #721c24; font-size: 14px; }}
            .buttons {{ text-align: center; margin-top: 30px; }}
            .help-text {{ font-size: 14px; color: #666; margin-top: 5px; }}
            .requirements {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            .requirements h4 {{ margin-top: 0; color: #495057; }}
            .requirements ul {{ margin-bottom: 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📤 {title}</h1>
            
            <div class="messages">
    """
    
    # Добавляем сообщения
    if messages.get_messages(request):
        for message in messages.get_messages(request):
            message_class = message.tags if message.tags else 'info'
            html += f'<div class="message {message_class}">{message}</div>'
    
    form_url = '/profiles/photos/upload/' if single else '/profiles/photos/upload-multiple/'
    
    html += f"""
            </div>
            
            <div class="requirements">
                <h4>📋 Требования к фотографиям:</h4>
                <ul>
                    <li>✅ Форматы: JPG, JPEG, PNG, GIF, WEBP</li>
                    <li>✅ Максимальный размер: 5MB на файл</li>
                    <li>✅ Минимальное разрешение: 200x200 пикселей</li>
                    <li>✅ Максимальное разрешение: 4000x4000 пикселей</li>
                    <li>✅ Максимум 10 фотографий на профиль</li>
                    {'<li>✅ Можно загрузить до 5 фотографий за раз</li>' if not single else ''}
                </ul>
            </div>
            
            <form method="post" action="{form_url}" enctype="multipart/form-data">
                <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
    """
    
    # Отображаем поля формы
    for field_name, field in form.fields.items():
        field_value = form.data.get(field_name, '') if form.is_bound else (getattr(form.instance, field_name, '') if hasattr(form, 'instance') else '')
        errors = form.errors.get(field_name, []) if form.is_bound else []
        
        html += f"""
                <div class="form-group">
                    <label for="id_{field_name}">{field.label}:</label>
        """
        
        if field_name == 'is_primary':
            checked = 'checked' if field_value or field.initial else ''
            html += f'<div class="form-check"><input type="checkbox" id="id_{field_name}" name="{field_name}" class="form-check-input" {checked}><label for="id_{field_name}">{field.label}</label></div>'
        else:
            multiple = 'multiple' if field_name == 'images' else ''
            html += f'<input type="file" id="id_{field_name}" name="{field_name}" class="form-control" accept="image/*" {multiple}>'
            if hasattr(field, 'help_text') and field.help_text:
                html += f'<div class="help-text">{field.help_text}</div>'
        
        if errors:
            html += '<ul class="errorlist">'
            for error in errors:
                html += f'<li>{error}</li>'
            html += '</ul>'
        
        html += '</div>'
    
    # Добавляем общие ошибки формы
    if form.non_field_errors():
        html += '<ul class="errorlist">'
        for error in form.non_field_errors():
            html += f'<li>{error}</li>'
        html += '</ul>'
    
    html += f"""
                <div class="buttons">
                    <button type="submit" class="btn">📤 {'Загрузить фотографию' if single else 'Загрузить фотографии'}</button>
                    <a href="/profiles/photos/" class="btn btn-secondary">📸 К фотографиям</a>
                    <a href="/" class="btn btn-secondary">🏠 Главная</a>
                </div>
            </form>
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html)


# ====================== РАСШИРЕННЫЙ ПОИСК ПРОФИЛЕЙ ======================



# ====================== СИСТЕМА СООБЩЕНИЙ ======================

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
    
    return render_conversations_list(request, conversation_data)


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
                    invalidate_unread_count_cache(other_user)  # У получателя появилось новое непрочитанное сообщение
                    
                    messages.success(request, 'Сообщение отправлено!')
                    return redirect('profiles:conversation_detail', conversation_id=conversation.id)
                else:
                    messages.error(request, error_msg)
    
    return render_conversation_detail(request, conversation, other_profile, messages_page, message_form)


@login_required
def start_conversation(request, user_id):
    """Начать новую переписку с пользователем"""
    try:
        other_user = User.objects.get(id=user_id)
        other_profile = Profile.objects.get(user=other_user)
    except (User.DoesNotExist, Profile.DoesNotExist):
        messages.error(request, 'Пользователь не найден!')
        return redirect('profiles:search_profiles')
    
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
        return redirect('profiles:search_profiles')
    
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
    
    return render_report_form(request, reported_profile, form)


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


# ====================== РЕНДЕРИНГ СТРАНИЦ СООБЩЕНИЙ ======================

def render_conversations_list(request, conversation_data):
    """Рендеринг списка переписок"""
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Мои сообщения - Сайт знакомств</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
            h1 {{ color: #333; text-align: center; margin-bottom: 30px; }}
            
            .header-actions {{ text-align: center; margin-bottom: 30px; }}
            .btn {{ padding: 12px 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; margin: 0 10px; text-decoration: none; display: inline-block; transition: transform 0.2s; }}
            .btn:hover {{ transform: translateY(-2px); }}
            .btn-secondary {{ background: #6c757d; }}
            
            .conversations-list {{ display: grid; gap: 15px; }}
            .conversation-item {{ background: #f8f9fa; border-radius: 10px; padding: 20px; border-left: 4px solid #667eea; transition: transform 0.2s, box-shadow 0.2s; cursor: pointer; }}
            .conversation-item:hover {{ transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
            .conversation-item.unread {{ border-left-color: #28a745; background: #f0fff4; }}
            
            .conv-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
            .conv-user {{ display: flex; align-items: center; }}
            .conv-avatar {{ font-size: 24px; margin-right: 15px; }}
            .conv-name {{ font-size: 18px; font-weight: bold; color: #333; }}
            .conv-time {{ color: #666; font-size: 14px; }}
            
            .conv-last-message {{ color: #555; margin-bottom: 10px; font-style: italic; }}
            .conv-preview {{ max-height: 40px; overflow: hidden; text-overflow: ellipsis; }}
            
            .conv-meta {{ display: flex; justify-content: space-between; align-items: center; }}
            .unread-badge {{ background: #28a745; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }}
            .conv-actions {{ display: flex; gap: 10px; }}
            .btn-small {{ padding: 6px 12px; font-size: 12px; }}
            
            .no-conversations {{ text-align: center; padding: 40px; color: #666; }}
            .messages {{ margin-bottom: 20px; }}
            .message {{ padding: 12px; border-radius: 8px; margin-bottom: 10px; }}
            .message.success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .message.error {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
            .message.info {{ background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>💬 Мои сообщения</h1>
            
            <div class="messages">
    """
    
    # Добавляем сообщения
    from django.contrib.messages import get_messages
    for message in get_messages(request):
        message_class = message.tags if message.tags else 'info'
        html += f'<div class="message {message_class}">{message}</div>'
    
    html += f"""
            </div>
            
            <div class="header-actions">
                <a href="/profiles/search/" class="btn">🔍 Найти собеседника</a>
                <a href="/profiles/advanced-search/" class="btn">🔍🔍 Расширенный поиск</a>
                <a href="/" class="btn btn-secondary">🏠 Главная</a>
            </div>
    """
    
    if conversation_data:
        html += '<div class="conversations-list">'
        
        for conv_data in conversation_data:
            conv = conv_data['conversation']
            other_profile = conv_data['other_profile']
            last_message = conv_data['last_message']
            unread_count = conv_data['unread_count']
            
            unread_class = 'unread' if unread_count > 0 else ''
            gender_icon = "👨" if other_profile.gender == 'male' else "👩"
            
            last_msg_preview = ''
            last_msg_time = ''
            if last_message:
                content = last_message.content[:100]
                if len(last_message.content) > 100:
                    content += '...'
                sender_prefix = 'Вы: ' if last_message.sender == request.user else f'{other_profile.nickname}: '
                last_msg_preview = f'{sender_prefix}{content}'
                last_msg_time = last_message.sent_at.strftime('%d.%m.%Y %H:%M')
            
            html += f"""
                <div class="conversation-item {unread_class}" onclick="window.location.href='/profiles/conversations/{conv.id}/'">
                    <div class="conv-header">
                        <div class="conv-user">
                            <div class="conv-avatar">{gender_icon}</div>
                            <div class="conv-name">{other_profile.nickname}</div>
                        </div>
                        <div class="conv-time">{last_msg_time}</div>
                    </div>
                    
                    {f'<div class="conv-last-message"><div class="conv-preview">{last_msg_preview}</div></div>' if last_msg_preview else ''}
                    
                    <div class="conv-meta">
                        <div>
                            <strong>Возраст:</strong> {other_profile.age} лет, 
                            <strong>Город:</strong> {other_profile.get_city_display()}
                        </div>
                        {f'<div class="unread-badge">{unread_count} новых</div>' if unread_count > 0 else ''}
                    </div>
                </div>
            """
        
        html += '</div>'
    else:
        html += """
            <div class="no-conversations">
                <h3>📭 У вас пока нет сообщений</h3>
                <p>Найдите интересных людей и начните общение!</p>
                <a href="/profiles/search/" class="btn">🔍 Найти собеседника</a>
            </div>
        """
    
    html += """
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html)


def render_conversation_detail(request, conversation, other_profile, messages_page, message_form):
    """Рендеринг детальной страницы переписки"""
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Переписка с {other_profile.nickname} - Сайт знакомств</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
            .container {{ max-width: 900px; margin: 0 auto; background: white; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); display: flex; flex-direction: column; height: 80vh; }}
            
            .chat-header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 15px 15px 0 0; }}
            .header-content {{ display: flex; justify-content: space-between; align-items: center; }}
            .user-info {{ display: flex; align-items: center; }}
            .user-avatar {{ font-size: 24px; margin-right: 15px; }}
            .user-details h2 {{ margin: 0; }}
            .user-details p {{ margin: 5px 0 0 0; opacity: 0.9; }}
            .header-actions {{ display: flex; gap: 10px; }}
            .btn {{ padding: 8px 16px; background: rgba(255,255,255,0.2); color: white; border: none; border-radius: 6px; text-decoration: none; font-size: 14px; transition: background 0.2s; }}
            .btn:hover {{ background: rgba(255,255,255,0.3); }}
            
            .messages-container {{ flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; }}
            .message-item {{ max-width: 70%; padding: 12px 16px; border-radius: 18px; word-wrap: break-word; }}
            .message-sent {{ align-self: flex-end; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-bottom-right-radius: 6px; }}
            .message-received {{ align-self: flex-start; background: #f1f3f4; color: #333; border-bottom-left-radius: 6px; }}
            .message-time {{ font-size: 11px; opacity: 0.7; margin-top: 5px; }}
            .message-status {{ font-size: 11px; opacity: 0.7; margin-top: 5px; }}
            
            .message-form {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 15px 15px; border-top: 1px solid #dee2e6; }}
            .form-row {{ display: flex; gap: 10px; align-items: end; }}
            .form-control {{ flex: 1; padding: 12px; border: 2px solid #e1e1e1; border-radius: 20px; resize: none; font-family: inherit; }}
            .form-control:focus {{ border-color: #667eea; outline: none; }}
            .btn-send {{ padding: 12px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 20px; font-weight: bold; cursor: pointer; }}
            .btn-send:hover {{ opacity: 0.9; }}
            .btn-send:disabled {{ opacity: 0.5; cursor: not-allowed; }}
            
            .form-help {{ font-size: 12px; color: #666; margin-top: 5px; }}
            .form-errors {{ color: #dc3545; font-size: 14px; margin-bottom: 10px; }}
            .no-messages {{ text-align: center; color: #666; padding: 40px; }}
            
            .messages {{ margin-bottom: 15px; }}
            .message {{ padding: 12px; border-radius: 8px; margin-bottom: 10px; }}
            .message.success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .message.error {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
            
            /* Стили пагинации для сообщений */
            .pagination {{ margin: 20px 0; text-align: center; }}
            .pagination-info {{ margin-bottom: 10px; color: #666; font-size: 12px; }}
            .pagination-controls {{ display: flex; justify-content: center; align-items: center; flex-wrap: wrap; gap: 3px; }}
            .btn-pagination {{ padding: 6px 10px; margin: 0 1px; text-decoration: none; border-radius: 4px; font-size: 12px; 
                               background: #f8f9fa; color: #333; border: 1px solid #dee2e6; transition: all 0.2s; }}
            .btn-pagination:hover {{ background: #e9ecef; transform: translateY(-1px); }}
            .btn-current {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-color: #667eea; }}
            .btn-current:hover {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); transform: none; }}
        </style>
        <script>
            function scrollToBottom() {{
                const container = document.querySelector('.messages-container');
                container.scrollTop = container.scrollHeight;
            }}
            
            window.addEventListener('load', scrollToBottom);
            
            function autoResize(textarea) {{
                textarea.style.height = 'auto';
                textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <div class="chat-header">
                <div class="header-content">
                    <div class="user-info">
                        <div class="user-avatar">{"👨" if other_profile.gender == 'male' else "👩"}</div>
                        <div class="user-details">
                            <h2>{other_profile.nickname}</h2>
                            <p>{other_profile.age} лет, {other_profile.get_city_display()}</p>
                        </div>
                    </div>
                    <div class="header-actions">
                        <a href="/profiles/view/{other_profile.id}/" class="btn">👁️ Профиль</a>
                        <a href="/profiles/report/{other_profile.user.id}/" class="btn">⚠️ Пожаловаться</a>
                        <a href="/profiles/conversations/" class="btn">📨 Все сообщения</a>
                    </div>
                </div>
            </div>
            
            <div class="messages">
    """
    
    # Добавляем системные сообщения
    from django.contrib.messages import get_messages
    for message in get_messages(request):
        message_class = message.tags if message.tags else 'info'
        html += f'<div class="message {message_class}">{message}</div>'
    
    html += '</div>'
    
    # Контейнер сообщений
    html += '<div class="messages-container">'
    
    if messages_page.object_list:
        for msg in messages_page.object_list:
            is_sent = msg.sender == request.user
            message_class = 'message-sent' if is_sent else 'message-received'
            
            # Форматируем время
            msg_time = msg.sent_at.strftime('%d.%m.%Y %H:%M')
            
            # Статус прочтения для отправленных сообщений
            read_status = ''
            if is_sent:
                if msg.is_read:
                    read_status = f'<div class="message-status">✓✓ Прочитано {msg.read_at.strftime("%H:%M") if msg.read_at else ""}</div>'
                else:
                    read_status = '<div class="message-status">✓ Доставлено</div>'
            
            html += f"""
                <div class="message-item {message_class}">
                    <div>{msg.content}</div>
                    <div class="message-time">{msg_time}</div>
                    {read_status}
                </div>
            """
    else:
        html += """
            <div class="no-messages">
                <h3>💭 Начните переписку</h3>
                <p>Отправьте первое сообщение!</p>
            </div>
        """
    
    html += '</div>'
    
    # Форма отправки сообщения
    form_errors = ''
    if message_form.errors:
        for field, errors in message_form.errors.items():
            for error in errors:
                form_errors += f'<div class="form-errors">{error}</div>'
    
    message_value = message_form.data.get('content', '') if message_form.is_bound else ''
    
    html += f"""
            <div class="message-form">
                {form_errors}
                <form method="post">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
                    <div class="form-row">
                        <textarea name="content" class="form-control" placeholder="Введите сообщение..." 
                                  rows="1" maxlength="1000" oninput="autoResize(this)" required>{message_value}</textarea>
                        <button type="submit" name="send_message" class="btn-send">Отправить</button>
                    </div>
                    <div class="form-help">Минимум 10 символов, максимум 1000. Запрещены контакты и ссылки.</div>
                </form>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Добавляем пагинацию для сообщений
    if messages_page.has_other_pages():
        html += """
            <div class="pagination">
                <div class="pagination-info">
        """
        html += f"""
                    Страница {messages_page.number} из {messages_page.paginator.num_pages} 
                    ({messages_page.start_index()}-{messages_page.end_index()} из {messages_page.paginator.count} сообщений)
        """
        html += """
                </div>
                <div class="pagination-controls">
        """
        
        # Получаем GET параметры (если есть)
        get_params = request.GET.copy()
        if 'page' in get_params:
            del get_params['page']
        query_string = '&' + get_params.urlencode() if get_params else ''
        
        # Первая страница
        if messages_page.has_previous():
            html += f'<a href="?page=1{query_string}" class="btn btn-pagination">« Первая</a>'
            html += f'<a href="?page={messages_page.previous_page_number()}{query_string}" class="btn btn-pagination">‹ Пред</a>'
        
        # Текущая страница и соседние
        start_page = max(1, messages_page.number - 2)
        end_page = min(messages_page.paginator.num_pages, messages_page.number + 2)
        
        for page_num in range(start_page, end_page + 1):
            if page_num == messages_page.number:
                html += f'<span class="btn btn-pagination btn-current">{page_num}</span>'
            else:
                html += f'<a href="?page={page_num}{query_string}" class="btn btn-pagination">{page_num}</a>'
        
        # Последняя страница
        if messages_page.has_next():
            html += f'<a href="?page={messages_page.next_page_number()}{query_string}" class="btn btn-pagination">След ›</a>'
            html += f'<a href="?page={messages_page.paginator.num_pages}{query_string}" class="btn btn-pagination">Последняя »</a>'
        
        html += """
                </div>
            </div>
        """

    # Обработка ошибок формы
    
    return HttpResponse(html)


def render_report_form(request, reported_profile, form):
    """Рендеринг формы жалобы"""
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    
    form_errors = ''
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                form_errors += f'<div class="form-errors">{error}</div>'
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Пожаловаться на {reported_profile.nickname} - Сайт знакомств</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
            h1 {{ color: #333; text-align: center; margin-bottom: 30px; }}
            
            .user-info {{ background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 30px; text-align: center; }}
            .user-avatar {{ font-size: 48px; margin-bottom: 10px; }}
            .user-name {{ font-size: 24px; font-weight: bold; color: #333; margin-bottom: 5px; }}
            .user-details {{ color: #666; }}
            
            .form-group {{ margin-bottom: 20px; }}
            .form-group label {{ display: block; margin-bottom: 8px; color: #333; font-weight: bold; }}
            .form-control {{ width: 100%; padding: 12px; border: 2px solid #e1e1e1; border-radius: 8px; font-size: 16px; box-sizing: border-box; }}
            .form-control:focus {{ border-color: #667eea; outline: none; }}
            
            .form-errors {{ color: #dc3545; font-size: 14px; margin-bottom: 15px; padding: 10px; background: #f8d7da; border-radius: 5px; }}
            .form-help {{ font-size: 14px; color: #666; margin-top: 5px; }}
            
            .form-actions {{ text-align: center; margin-top: 30px; }}
            .btn {{ padding: 12px 24px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; margin: 0 10px; text-decoration: none; display: inline-block; transition: transform 0.2s; }}
            .btn:hover {{ transform: translateY(-2px); }}
            .btn-primary {{ background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white; }}
            .btn-secondary {{ background: #6c757d; color: white; }}
            
            .warning {{ background: #fff3cd; color: #856404; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #ffeeba; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚠️ Пожаловаться на пользователя</h1>
            
            <div class="user-info">
                <div class="user-avatar">{"👨" if reported_profile.gender == 'male' else "👩"}</div>
                <div class="user-name">{reported_profile.nickname}</div>
                <div class="user-details">{reported_profile.age} лет, {reported_profile.get_city_display()}</div>
            </div>
            
            <div class="warning">
                <strong>Важно:</strong> Жалобы рассматриваются администрацией. Ложные жалобы могут повлечь блокировку вашего аккаунта.
            </div>
            
            {form_errors}
            
            <form method="post">
                <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
                
                <div class="form-group">
                    <label for="id_reason">Причина жалобы:</label>
                    <select id="id_reason" name="reason" class="form-control" required>
    """
    
    for value, label in form.fields['reason'].choices:
        selected = 'selected' if form.data.get('reason') == value else ''
        html += f'<option value="{value}" {selected}>{label}</option>'
    
    description_value = form.data.get('description', '') if form.is_bound else ''
    
    html += f"""
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="id_description">Дополнительные сведения (необязательно):</label>
                    <textarea id="id_description" name="description" class="form-control" rows="4" 
                              placeholder="Опишите проблему подробнее..." maxlength="500">{description_value}</textarea>
                    <div class="form-help">Максимум 500 символов</div>
                </div>
                
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">📤 Отправить жалобу</button>
                    <a href="/profiles/view/{reported_profile.id}/" class="btn btn-secondary">❌ Отмена</a>
                </div>
            </form>
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html)


def get_user_profile(user, use_cache=True):
    """Получить профиль пользователя с кэшированием"""
    # Эта функция заменена на get_cached_user_profile из cache_utils.py
    return get_cached_user_profile(user, use_cache)


def invalidate_user_profile_cache(user):
    """Очистить кэш профиля пользователя"""
    # Эта функция заменена на функцию из cache_utils.py
    invalidate_user_profile_cache(user)
