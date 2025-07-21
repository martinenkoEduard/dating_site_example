from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from ..models import Profile
from ..forms import ProfileForm, ProfileSearchForm
from ..cache_utils import (
    get_cached_user_profile, invalidate_user_profile_cache,
    get_cached_profile_stats, get_cached_recent_profiles,
    invalidate_search_cache
)


def home(request):
    """Главная страница с кэшированными данными"""
    
    # Получаем кэшированную статистику профилей
    stats = get_cached_profile_stats()
    
    # Проверяем наличие профиля у пользователя (если авторизован)
    has_profile = False
    if request.user.is_authenticated:
        user_profile = get_cached_user_profile(request.user)
        has_profile = user_profile is not None
    
    # Получаем кэшированный список новых профилей
    recent_profiles = get_cached_recent_profiles(limit=6)
    
    context = {
        'total_profiles': stats.get('total', 0),
        'male_profiles': stats.get('male', 0),
        'female_profiles': stats.get('female', 0),
        'has_profile': has_profile,
        'recent_profiles': recent_profiles
    }
    
    return render(request, 'home.html', context)


@login_required
def create_profile(request):
    """Создание нового профиля"""
    # Проверяем, есть ли уже профиль у пользователя
    if Profile.objects.filter(user=request.user).exists():
        messages.info(request, 'У вас уже есть профиль. Вы можете его редактировать.')
        return redirect('profiles:my_profile')
    
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, 'Профиль успешно создан!')
            return redirect('profiles:my_profile')
        else:
            messages.error(request, 'Ошибки в форме. Проверьте введенные данные.')
    else:
        form = ProfileForm()
    
    context = {
        'form': form,
        'title': 'Создание профиля',
        'action': 'create'
    }
    return render(request, 'profiles/profile_form.html', context)


@login_required
def my_profile(request):
    """Просмотр собственного профиля"""
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        messages.info(request, 'У вас еще нет профиля. Создайте его!')
        return redirect('profiles:create_profile')
    
    # Получаем все фотографии профиля
    photos = profile.photos.filter(is_verified=True).order_by('-is_primary', '-uploaded_at')
    
    context = {
        'profile': profile,
        'photos': photos,
        'is_own': True,
    }
    
    return render(request, 'profiles/profile_view.html', context)


@login_required
def edit_profile(request):
    """Редактирование профиля с инвалидацией кэша"""
    try:
        profile = get_cached_user_profile(request.user, use_cache=False)  # Получаем свежие данные
    except Profile.DoesNotExist:
        messages.info(request, 'У вас еще нет профиля. Создайте его!')
        return redirect('profiles:create_profile')
    
    if not profile:
        messages.info(request, 'У вас еще нет профиля. Создайте его!')
        return redirect('profiles:create_profile')
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            
            # Инвалидируем все связанные кэши
            invalidate_user_profile_cache(request.user)
            invalidate_search_cache()  # Поскольку профиль изменился, результаты поиска могут измениться
            
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('profiles:my_profile')
        else:
            messages.error(request, 'Ошибки в форме. Проверьте введенные данные.')
    else:
        form = ProfileForm(instance=profile)
    
    context = {
        'form': form,
        'title': 'Редактирование профиля',
        'action': 'edit'
    }
    return render(request, 'profiles/profile_form.html', context)


def view_profile(request, profile_id):
    """Просмотр чужого профиля"""
    try:
        profile = get_object_or_404(Profile, id=profile_id)
        
        # Получаем все фотографии профиля
        photos = profile.photos.filter(is_verified=True).order_by('-is_primary', '-uploaded_at')
        
        context = {
            'profile': profile,
            'photos': photos,
            'is_own': False,
        }
        
        return render(request, 'profiles/profile_view.html', context)
    except Profile.DoesNotExist:
        messages.error(request, f'Профиль с ID {profile_id} не найден.')
        return redirect('/')
    except Exception as e:
        messages.error(request, f'Ошибка при загрузке профиля: {str(e)}')
        return redirect('/')


@login_required
def search_profiles(request):
    """Поиск профилей с кэшированием результатов"""
    try:
        own_profile = get_cached_user_profile(request.user)
    except Profile.DoesNotExist:
        messages.info(request, 'Сначала создайте свой профиль!')
        return redirect('profiles:create_profile')
    
    if not own_profile:
        messages.info(request, 'Сначала создайте свой профиль!')
        return redirect('profiles:create_profile')
    
    form = ProfileSearchForm(request.GET or None)
    
    # Выполняем поиск
    profiles = Profile.objects.search_optimized(exclude_user=request.user)
    
    # Применяем фильтры если форма валидна
    if form.is_valid():
        data = form.cleaned_data
        
        # Фильтр по полу
        if data.get('gender'):
            profiles = profiles.filter(gender=data['gender'])
        
        # Фильтр по возрасту
        if data.get('age_min'):
            profiles = profiles.filter(age__gte=data['age_min'])
        if data.get('age_max'):
            profiles = profiles.filter(age__lte=data['age_max'])
        
        # Фильтр по росту
        if data.get('height_min'):
            profiles = profiles.filter(height__gte=data['height_min'])
        if data.get('height_max'):
            profiles = profiles.filter(height__lte=data['height_max'])
        
        # Фильтр по городу
        if data.get('city'):
            profiles = profiles.filter(city=data['city'])
        
        # Фильтр по образованию
        if data.get('education'):
            profiles = profiles.filter(education=data['education'])
        
        # Фильтр по занятости
        if data.get('employment'):
            profiles = profiles.filter(employment=data['employment'])
        
        # Фильтр по курению
        if data.get('smoking'):
            profiles = profiles.filter(smoking=data['smoking'])
        
        # Фильтр по алкоголю
        if data.get('alcohol'):
            profiles = profiles.filter(alcohol=data['alcohol'])
        
        # Фильтр по наличию детей
        if data.get('has_children') is not None:
            profiles = profiles.filter(has_children=data['has_children'])
    
    # Подсчитываем общее количество
    total_count = profiles.count()
    
    # Применяем пагинацию
    paginator = Paginator(profiles, 12)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.get_page(1)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'total_count': total_count,
        'profiles': page_obj.object_list
    }
    
    return render(request, 'profiles/search_results.html', context)
