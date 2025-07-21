from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse

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


from ..models import Profile
from ..forms import ProfileForm, ProfileSearchForm, AdvancedProfileSearchForm
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
    
    return render_profile_form(request, form, 'Создание профиля', 'create')


@login_required
def my_profile(request):
    """Просмотр собственного профиля"""
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        messages.info(request, 'У вас еще нет профиля. Создайте его!')
        return redirect('profiles:create_profile')
    
    return render_profile_view(request, profile, is_own=True)


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
    
    return render_profile_form(request, form, 'Редактирование профиля', 'edit')


def view_profile(request, profile_id):
    """Просмотр чужого профиля"""
    try:
        profile = get_object_or_404(Profile, id=profile_id)
        return render_profile_view(request, profile, is_own=False)
    except Profile.DoesNotExist:
        messages.error(request, f'Профиль с ID {profile_id} не найден.')
        return redirect('/')
    except Exception as e:
        messages.error(request, f'Ошибка при загрузке профиля: {str(e)}')
        return redirect('/')


def render_profile_form(request, form, title, action):
    """Рендеринг формы профиля"""
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
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
            h1 {{ color: #333; text-align: center; margin-bottom: 30px; }}
            .form-section {{ margin-bottom: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px; }}
            .form-section h3 {{ color: #495057; margin-bottom: 15px; border-bottom: 2px solid #dee2e6; padding-bottom: 10px; }}
            .form-row {{ display: flex; flex-wrap: wrap; margin-bottom: 15px; }}
            .form-group {{ margin-bottom: 15px; flex: 1; min-width: 300px; margin-right: 15px; }}
            .form-group:last-child {{ margin-right: 0; }}
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
        </style>
    </head>
    <body>
        <div class="container">
            <h1>👤 {title}</h1>
            
            <div class="messages">
    """
    
    # Добавляем сообщения
    if messages.get_messages(request):
        for message in messages.get_messages(request):
            message_class = 'success' if message.tags == 'success' else ('error' if message.tags == 'error' else 'info')
            html += f'<div class="message {message_class}">{message}</div>'
    
    # URL для формы
    form_url = '/profiles/create/' if action == 'create' else '/profiles/edit/'
    
    html += f"""
            </div>
            
            <form method="post" action="{form_url}">
                <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
                
                <div class="form-section">
                    <h3>📝 Основная информация</h3>
                    <div class="form-row">
    """
    
    # Основные поля
    basic_fields = ['nickname', 'age', 'height', 'weight', 'blood_group', 'gender', 'city']
    for field_name in basic_fields:
        if field_name in form.fields:
            field = form.fields[field_name]
            field_value = form.data.get(field_name, '') if form.is_bound else (getattr(form.instance, field_name, '') if form.instance else '')
            errors = form.errors.get(field_name, []) if form.is_bound else []
            
            html += f"""
                        <div class="form-group">
                            <label for="id_{field_name}">{field.label}:</label>
            """
            
            if field_name in ['gender', 'city', 'blood_group']:
                html += f'<select id="id_{field_name}" name="{field_name}" class="form-control">'
                html += '<option value="">---------</option>'
                for value, label in field.choices:
                    selected = 'selected' if str(field_value) == str(value) else ''
                    html += f'<option value="{value}" {selected}>{label}</option>'
                html += '</select>'
            else:
                input_type = 'number' if field_name in ['age', 'height', 'weight'] else 'text'
                html += f'<input type="{input_type}" id="id_{field_name}" name="{field_name}" value="{field_value}" class="form-control">'
            
            if errors:
                html += '<ul class="errorlist">'
                for error in errors:
                    html += f'<li>{error}</li>'
                html += '</ul>'
            
            html += '</div>'
    
    html += """
                    </div>
                </div>
                
                <div class="form-section">
                    <h3>💝 Личная информация</h3>
                    <div class="form-row">
    """
    
    # Личная информация
    personal_fields = ['orientation', 'marital_status', 'education', 'employment', 'goal']
    for field_name in personal_fields:
        if field_name in form.fields:
            field = form.fields[field_name]
            field_value = form.data.get(field_name, '') if form.is_bound else (getattr(form.instance, field_name, '') if form.instance else '')
            errors = form.errors.get(field_name, []) if form.is_bound else []
            
            html += f"""
                        <div class="form-group">
                            <label for="id_{field_name}">{field.label}:</label>
            """
            
            if field_name == 'goal':
                html += f'<textarea id="id_{field_name}" name="{field_name}" class="form-control" rows="3">{field_value}</textarea>'
            elif field_name in ['orientation', 'marital_status', 'education', 'employment']:
                html += f'<select id="id_{field_name}" name="{field_name}" class="form-control">'
                html += '<option value="">---------</option>'
                for value, label in field.choices:
                    selected = 'selected' if str(field_value) == str(value) else ''
                    html += f'<option value="{value}" {selected}>{label}</option>'
                html += '</select>'
            
            if errors:
                html += '<ul class="errorlist">'
                for error in errors:
                    html += f'<li>{error}</li>'
                html += '</ul>'
            
            html += '</div>'
    
    html += """
                    </div>
                </div>
                
                <div class="form-section">
                    <h3>🏃 Образ жизни и здоровье</h3>
                    <div class="form-row">
    """
    
    # Образ жизни
    lifestyle_fields = ['smoking', 'alcohol', 'sport', 'health_rating', 'has_diseases']
    for field_name in lifestyle_fields:
        if field_name in form.fields:
            field = form.fields[field_name]
            field_value = form.data.get(field_name, '') if form.is_bound else (getattr(form.instance, field_name, '') if form.instance else '')
            errors = form.errors.get(field_name, []) if form.is_bound else []
            
            if field_name == 'has_diseases':
                checked = 'checked' if field_value else ''
                html += f"""
                        <div class="form-group">
                            <div class="form-check">
                                <input type="checkbox" id="id_{field_name}" name="{field_name}" class="form-check-input" {checked}>
                                <label for="id_{field_name}">{field.label}</label>
                            </div>
                        </div>
                """
            else:
                html += f"""
                        <div class="form-group">
                            <label for="id_{field_name}">{field.label}:</label>
                """
                
                if field_name in ['smoking', 'alcohol', 'sport']:
                    html += f'<select id="id_{field_name}" name="{field_name}" class="form-control">'
                    html += '<option value="">---------</option>'
                    for value, label in field.choices:
                        selected = 'selected' if str(field_value) == str(value) else ''
                        html += f'<option value="{value}" {selected}>{label}</option>'
                    html += '</select>'
                else:  # health_rating
                    html += f'<input type="number" id="id_{field_name}" name="{field_name}" value="{field_value}" class="form-control" min="1" max="10">'
                
                if errors:
                    html += '<ul class="errorlist">'
                    for error in errors:
                        html += f'<li>{error}</li>'
                    html += '</ul>'
                
                html += '</div>'
    
    html += """
                    </div>
                </div>
                
                <div class="buttons">
                    <button type="submit" class="btn">💾 Сохранить</button>
                    <a href="/" class="btn btn-secondary">🏠 На главную</a>
                </div>
            </form>
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html)


def render_profile_view(request, profile, is_own=False):
    """Рендеринг просмотра профиля"""
    
    # Получаем все фотографии профиля
    photos = profile.photos.filter(is_verified=True).order_by('-is_primary', '-uploaded_at')
    
    context = {
        'profile': profile,
        'photos': photos,
        'is_own': is_own,
    }
    
    return render(request, 'profile_view.html', context)


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
    
    # Создаем параметры поиска для кэширования
    search_params = {}
    if request.GET:
        search_params = dict(request.GET.items())
        search_params['user_id'] = request.user.id  # Добавляем ID пользователя для уникальности
    
    # Пытаемся получить кэшированные результаты
    cached_results = None
    if search_params:
        cached_results = get_cached_search_results(search_params)
    
    if cached_results:
        # Используем кэшированные результаты
        profiles_list = cached_results['results']
        total_count = cached_results['total_count']
        
        # Применяем пагинацию к кэшированным результатам
        paginator = Paginator(profiles_list, 12)
        page_number = request.GET.get('page', 1)
        
        try:
            page_obj = paginator.get_page(page_number)
        except (PageNotAnInteger, EmptyPage):
            page_obj = paginator.get_page(1)
    else:
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
        
        # Подсчитываем общее количество и преобразуем в список
        total_count = profiles.count()
        profiles_list = list(profiles)
        
        # Кэшируем результаты поиска
        if search_params:
            cache_search_results_data(search_params, profiles_list, total_count, timeout=600)
        
        # Применяем пагинацию
        paginator = Paginator(profiles_list, 12)
        page_number = request.GET.get('page', 1)
        
        try:
            page_obj = paginator.get_page(page_number)
        except (PageNotAnInteger, EmptyPage):
            page_obj = paginator.get_page(1)
    
    return render_search_results(request, form, page_obj, total_count)


def render_search_results(request, form, page_obj, total_count):
    """Рендеринг результатов поиска профилей с пагинацией"""
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Поиск профилей - Сайт знакомств</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
            h1 {{ color: #333; text-align: center; margin-bottom: 30px; }}
            .search-section {{ background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
            .search-form {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
            .form-group {{ margin-bottom: 15px; }}
            .form-group label {{ display: block; margin-bottom: 5px; color: #333; font-weight: bold; font-size: 14px; }}
            .form-control {{ width: 100%; padding: 10px; border: 2px solid #e1e1e1; border-radius: 5px; font-size: 14px; box-sizing: border-box; }}
            .form-control:focus {{ border-color: #667eea; outline: none; }}
            .search-buttons {{ grid-column: 1 / -1; text-align: center; margin-top: 15px; }}
            .btn {{ padding: 12px 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; margin: 0 10px; text-decoration: none; display: inline-block; }}
            .btn:hover {{ transform: translateY(-2px); }}
            .btn-secondary {{ background: #6c757d; }}
            .btn-clear {{ background: #ffc107; color: #333; }}
            .results-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
            .results-count {{ color: #666; }}
            .profiles-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }}
            .profile-card {{ background: #f8f9fa; border-radius: 10px; padding: 20px; border-left: 4px solid #667eea; transition: transform 0.2s; }}
            .profile-card:hover {{ transform: translateY(-5px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
            .profile-header {{ display: flex; align-items: center; margin-bottom: 15px; }}
            .profile-icon {{ font-size: 24px; margin-right: 10px; }}
            .profile-name {{ font-size: 18px; font-weight: bold; color: #333; }}
            .profile-info {{ margin-bottom: 10px; }}
            .profile-info strong {{ color: #495057; }}
            .profile-goal {{ background: white; padding: 10px; border-radius: 5px; font-style: italic; color: #666; margin-bottom: 15px; }}
            .profile-actions {{ text-align: center; }}
            .btn-small {{ padding: 8px 16px; font-size: 14px; }}
            .no-results {{ text-align: center; padding: 40px; color: #666; }}
            .messages {{ margin-bottom: 20px; }}
            .message {{ padding: 12px; border-radius: 8px; margin-bottom: 10px; }}
            .message.info {{ background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }}
            
            /* Стили пагинации */
            .pagination {{ margin: 30px 0; text-align: center; }}
            .pagination-info {{ margin-bottom: 15px; color: #666; font-size: 14px; }}
            .pagination-controls {{ display: flex; justify-content: center; align-items: center; flex-wrap: wrap; gap: 5px; }}
            .btn-pagination {{ padding: 8px 12px; margin: 0 2px; text-decoration: none; border-radius: 5px; font-size: 14px; 
                               background: #f8f9fa; color: #333; border: 1px solid #dee2e6; transition: all 0.2s; }}
            .btn-pagination:hover {{ background: #e9ecef; transform: translateY(-1px); }}
            .btn-current {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-color: #667eea; }}
            .btn-current:hover {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); transform: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 Поиск профилей</h1>
            
            <div class="messages">
    """
    
    # Добавляем сообщения
    if hasattr(request, '_messages'):
        for message in request._messages:
            html += f'<div class="message info">{message}</div>'
    
    html += f"""
            </div>
            
            <div class="search-section">
                <form method="get" class="search-form">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
    """
    
    # Добавляем поля формы поиска
    for field_name, field in form.fields.items():
        field_value = form.data.get(field_name, '') if form.is_bound else ''
        
        html += f"""
                    <div class="form-group">
                        <label for="id_{field_name}">{field.label}:</label>
        """
        
        if hasattr(field, 'choices') and field.choices:
            html += f'<select id="id_{field_name}" name="{field_name}" class="form-control">'
            for value, label in field.choices:
                selected = 'selected' if str(field_value) == str(value) else ''
                html += f'<option value="{value}" {selected}>{label}</option>'
            html += '</select>'
        else:
            input_type = 'number' if field_name in ['age_min', 'age_max', 'height_min', 'height_max'] else 'text'
            placeholder = field.widget.attrs.get('placeholder', '')
            html += f'<input type="{input_type}" id="id_{field_name}" name="{field_name}" value="{field_value}" class="form-control" placeholder="{placeholder}">'
        
        html += '</div>'
    
    html += f"""
                    <div class="search-buttons">
                        <button type="submit" class="btn">🔍 Найти</button>
                        <a href="/profiles/advanced-search/" class="btn">🔍🔍 Расширенный поиск</a>
                        <a href="/profiles/search/" class="btn btn-clear">🗑️ Очистить</a>
                        <a href="/" class="btn btn-secondary">🏠 Главная</a>
                    </div>
                </form>
            </div>
            
            <div class="results-header">
                <h2>Результаты поиска</h2>
                <div class="results-count">Найдено: {total_count} профилей (показано: {len(page_obj)})</div>
            </div>
    """
    
    if page_obj.object_list:
        html += '<div class="profiles-grid">'
        
        for profile in page_obj.object_list:
            gender_icon = "👨" if profile.gender == 'male' else "👩"
            last_online = profile.last_online.strftime('%d.%m.%Y %H:%M')
            
            # Получаем главную фотографию
            main_photo = profile.photos.filter(is_primary=True).first()
            photo_url = main_photo.image.url if main_photo and main_photo.image else None
            
            html += f"""
                <div class="profile-card">
                    <div class="profile-header">
                        <div class="profile-icon">{gender_icon}</div>
                        <div class="profile-name">{profile.nickname}</div>
                    </div>
            """
            
            # Добавляем фотографию если есть
            if photo_url:
                try:
                    html += f"""
                        <div class="profile-photo">
                            <img src="{photo_url}" alt="Фото {profile.nickname}" 
                                 style="width: 100%; height: 200px; object-fit: cover; border-radius: 8px; margin-bottom: 15px;"
                                 onerror="this.style.display='none';">
                        </div>
                    """
                except Exception:
                    # Пропускаем фотографии с ошибками
                    pass
            
            html += f"""
                    <div class="profile-info">
                        <strong>Возраст:</strong> {profile.age} лет
                    </div>
                    <div class="profile-info">
                        <strong>Город:</strong> {profile.get_city_display()}
                    </div>
                    <div class="profile-info">
                        <strong>Рост:</strong> {profile.height} см
                    </div>
                    <div class="profile-info">
                        <strong>Образование:</strong> {profile.get_education_display()}
                    </div>
                    <div class="profile-info">
                        <strong>Последний заход:</strong> {last_online}
                    </div>
                    <div class="profile-goal">
                        "{profile.goal[:100]}{'...' if len(profile.goal) > 100 else ''}"
                    </div>
                    <div class="profile-actions">
                        <a href="/profiles/view/{profile.id}/" class="btn btn-small">👁️ Посмотреть</a>
                        <a href="/profiles/message/{profile.user.id}/" class="btn btn-small">💌 Написать</a>
                    </div>
                </div>
            """
        
        html += '</div>'
        
        if total_count > 50:
            html += f"""
            <div style="text-align: center; margin-top: 20px; padding: 15px; background: #fff3cd; border-radius: 5px;">
                <p><strong>Показано первых 50 профилей из {total_count}.</strong></p>
                <p>Используйте фильтры для уточнения поиска.</p>
            </div>
            """
    else:
        html += """
            <div class="no-results">
                <h3>😔 Профили не найдены</h3>
                <p>Попробуйте изменить параметры поиска или очистить фильтры.</p>
            </div>
        """
    
    # Добавляем пагинацию
    if page_obj.has_other_pages():
        html += """
            <div class="pagination">
                <div class="pagination-info">
        """
        html += f"""
                    Страница {page_obj.number} из {page_obj.paginator.num_pages} 
                    ({page_obj.start_index()}-{page_obj.end_index()} из {total_count} профилей)
        """
        html += """
                </div>
                <div class="pagination-controls">
        """
        
        # Получаем GET параметры для сохранения фильтров
        get_params = request.GET.copy()
        if 'page' in get_params:
            del get_params['page']
        query_string = '&' + get_params.urlencode() if get_params else ''
        
        # Первая страница
        if page_obj.has_previous():
            html += f'<a href="?page=1{query_string}" class="btn btn-pagination">« Первая</a>'
            html += f'<a href="?page={page_obj.previous_page_number()}{query_string}" class="btn btn-pagination">‹ Предыдущая</a>'
        
        # Текущая страница и соседние
        start_page = max(1, page_obj.number - 2)
        end_page = min(page_obj.paginator.num_pages, page_obj.number + 2)
        
        for page_num in range(start_page, end_page + 1):
            if page_num == page_obj.number:
                html += f'<span class="btn btn-pagination btn-current">{page_num}</span>'
            else:
                html += f'<a href="?page={page_num}{query_string}" class="btn btn-pagination">{page_num}</a>'
        
        # Последняя страница
        if page_obj.has_next():
            html += f'<a href="?page={page_obj.next_page_number()}{query_string}" class="btn btn-pagination">Следующая ›</a>'
            html += f'<a href="?page={page_obj.paginator.num_pages}{query_string}" class="btn btn-pagination">Последняя »</a>'
        
        html += """
                </div>
            </div>
        """

    html += """
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html)




@login_required
def advanced_search_profiles(request):
    """Расширенный поиск и фильтрация профилей с множественными критериями"""
    
    # Получаем собственный профиль для исключения из результатов
    try:
        own_profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        messages.info(request, 'Сначала создайте свой профиль!')
        return redirect('profiles:create_profile')
    
    # Инициализируем форму расширенного поиска
    form = AdvancedProfileSearchForm(request.GET or None)
    profiles = Profile.objects.exclude(user=request.user).filter(is_active=True)
    
    # Применяем фильтры если форма валидна
    if form.is_valid():
        data = form.cleaned_data
        
        # ========== ОСНОВНЫЕ ФИЛЬТРЫ ==========
        if data.get('gender'):
            profiles = profiles.filter(gender=data['gender'])
        
        if data.get('age_min'):
            profiles = profiles.filter(age__gte=data['age_min'])
        if data.get('age_max'):
            profiles = profiles.filter(age__lte=data['age_max'])
        
        if data.get('city'):
            profiles = profiles.filter(city__in=data['city'])
        
        # ========== ФИЗИЧЕСКИЕ ПАРАМЕТРЫ ==========
        if data.get('height_min'):
            profiles = profiles.filter(height__gte=data['height_min'])
        if data.get('height_max'):
            profiles = profiles.filter(height__lte=data['height_max'])
        
        if data.get('weight_min'):
            profiles = profiles.filter(weight__gte=data['weight_min'])
        if data.get('weight_max'):
            profiles = profiles.filter(weight__lte=data['weight_max'])
        
        if data.get('blood_group'):
            profiles = profiles.filter(blood_group__in=data['blood_group'])
        
        # ========== ОБРАЗОВАНИЕ И КАРЬЕРА ==========
        if data.get('education'):
            profiles = profiles.filter(education__in=data['education'])
        
        if data.get('employment'):
            profiles = profiles.filter(employment__in=data['employment'])
        
        # ========== ОБРАЗ ЖИЗНИ ==========
        if data.get('smoking'):
            profiles = profiles.filter(smoking__in=data['smoking'])
        
        if data.get('alcohol'):
            profiles = profiles.filter(alcohol__in=data['alcohol'])
        
        if data.get('sport'):
            profiles = profiles.filter(sport__in=data['sport'])
        
        if data.get('health_rating_min'):
            profiles = profiles.filter(health_rating__gte=data['health_rating_min'])
        if data.get('health_rating_max'):
            profiles = profiles.filter(health_rating__lte=data['health_rating_max'])
        
        # ========== СЕМЕЙНЫЕ ОТНОШЕНИЯ ==========
        if data.get('marital_status'):
            profiles = profiles.filter(marital_status__in=data['marital_status'])
        
        if data.get('orientation'):
            profiles = profiles.filter(orientation__in=data['orientation'])
        
        if data.get('has_children'):
            has_children_bool = data['has_children'] == 'True'
            profiles = profiles.filter(has_children=has_children_bool)
        
        if data.get('has_diseases'):
            has_diseases_bool = data['has_diseases'] == 'True'
            profiles = profiles.filter(has_diseases=has_diseases_bool)
        
        # ========== ЦЕЛЬ ПОИСКА ==========
        if data.get('conception_method'):
            profiles = profiles.filter(conception_method__in=data['conception_method'])
        
        if data.get('father_contact'):
            profiles = profiles.filter(father_contact__in=data['father_contact'])
        
        if data.get('payment_approach'):
            profiles = profiles.filter(payment_approach__in=data['payment_approach'])
        
        # ========== ПОИСК ПО ТЕКСТУ ==========
        if data.get('search'):
            search_term = data['search']
            profiles = profiles.filter(
                Q(nickname__icontains=search_term) | 
                Q(goal__icontains=search_term)
            )
        
        # ========== СПЕЦИАЛЬНЫЕ ФИЛЬТРЫ ==========
        # Только с фотографиями
        if data.get('with_photos_only'):
            profiles = profiles.filter(photos__isnull=False).distinct()
        
        # Фильтр по активности
        if data.get('online_recently'):
            from django.utils import timezone
            from datetime import timedelta
            
            now = timezone.now()
            if data['online_recently'] == '24h':
                profiles = profiles.filter(last_online__gte=now - timedelta(hours=24))
            elif data['online_recently'] == '3d':
                profiles = profiles.filter(last_online__gte=now - timedelta(days=3))
            elif data['online_recently'] == 'week':
                profiles = profiles.filter(last_online__gte=now - timedelta(weeks=1))
            elif data['online_recently'] == 'month':
                profiles = profiles.filter(last_online__gte=now - timedelta(days=30))
        
        # ========== СОРТИРОВКА ==========
        sort_by = data.get('sort_by', '-last_online')
        if sort_by:
            profiles = profiles.order_by(sort_by)
    else:
        # По умолчанию сортируем по последней активности
        profiles = profiles.order_by('-last_online')
    
    # Применяем пагинацию
    total_count = profiles.count()
    paginator = Paginator(profiles, 12)  # 12 профилей на страницу (3x4 сетка)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)
    
    return render_advanced_search_results(request, form, page_obj, total_count)





def render_advanced_search_results(request, form, page_obj, total_count):
    """Рендеринг страницы расширенного поиска профилей с пагинацией"""
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Расширенный поиск профилей - Сайт знакомств</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
            .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
            h1 {{ color: #333; text-align: center; margin-bottom: 30px; }}
            
            /* Фильтры */
            .filters-section {{ background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
            .filters-toggle {{ text-align: center; margin-bottom: 20px; }}
            .filters-form {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
            .filter-group {{ background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea; }}
            .filter-group h4 {{ margin-top: 0; color: #495057; border-bottom: 1px solid #dee2e6; padding-bottom: 8px; }}
            .form-row {{ display: flex; gap: 10px; align-items: end; margin-bottom: 15px; }}
            .form-group {{ flex: 1; }}
            .form-group label {{ display: block; margin-bottom: 5px; color: #333; font-weight: bold; font-size: 14px; }}
            .form-control {{ width: 100%; padding: 8px; border: 2px solid #e1e1e1; border-radius: 5px; font-size: 14px; box-sizing: border-box; }}
            .form-control:focus {{ border-color: #667eea; outline: none; }}
            
            /* Чекбоксы */
            .checkbox-list {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 5px; max-height: 120px; overflow-y: auto; }}
            .checkbox-list input[type="checkbox"] {{ margin-right: 8px; }}
            .checkbox-list label {{ font-weight: normal; font-size: 13px; cursor: pointer; }}
            
            /* Кнопки */
            .btn {{ padding: 12px 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; margin: 0 10px; text-decoration: none; display: inline-block; transition: transform 0.2s; }}
            .btn:hover {{ transform: translateY(-2px); }}
            .btn-secondary {{ background: #6c757d; }}
            .btn-clear {{ background: #ffc107; color: #333; }}
            
            /* Результаты */
            .results-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
            .results-count {{ color: #666; }}
            .profiles-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }}
            .profile-card {{ background: #f8f9fa; border-radius: 10px; padding: 20px; border-left: 4px solid #667eea; transition: transform 0.2s; }}
            .profile-card:hover {{ transform: translateY(-5px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
            .profile-header {{ display: flex; align-items: center; margin-bottom: 15px; }}
            .profile-icon {{ font-size: 24px; margin-right: 10px; }}
            .profile-name {{ font-size: 18px; font-weight: bold; color: #333; }}
            .profile-info {{ margin-bottom: 8px; font-size: 14px; }}
            .profile-info strong {{ color: #495057; }}
            .profile-goal {{ background: white; padding: 10px; border-radius: 5px; font-style: italic; color: #666; margin-bottom: 15px; font-size: 13px; }}
            .profile-actions {{ text-align: center; }}
            .btn-small {{ padding: 8px 16px; font-size: 14px; }}
            .no-results {{ text-align: center; padding: 40px; color: #666; }}
            .messages {{ margin-bottom: 20px; }}
            .message {{ padding: 12px; border-radius: 8px; margin-bottom: 10px; }}
            .message.info {{ background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }}
            
            /* Скрытие/показ фильтров */
            .filters-content {{ display: none; }}
            .filters-content.show {{ display: block; }}
            
            /* Стили пагинации */
            .pagination {{ margin: 30px 0; text-align: center; }}
            .pagination-info {{ margin-bottom: 15px; color: #666; font-size: 14px; }}
            .pagination-controls {{ display: flex; justify-content: center; align-items: center; flex-wrap: wrap; gap: 5px; }}
            .btn-pagination {{ padding: 8px 12px; margin: 0 2px; text-decoration: none; border-radius: 5px; font-size: 14px; 
                               background: #f8f9fa; color: #333; border: 1px solid #dee2e6; transition: all 0.2s; }}
            .btn-pagination:hover {{ background: #e9ecef; transform: translateY(-1px); }}
            .btn-current {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-color: #667eea; }}
            .btn-current:hover {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); transform: none; }}
        </style>
        <script>
            function toggleFilters() {{
                const content = document.getElementById('filters-content');
                const btn = document.getElementById('toggle-btn');
                if (content.classList.contains('show')) {{
                    content.classList.remove('show');
                    btn.textContent = '🔍 Показать фильтры';
                }} else {{
                    content.classList.add('show');
                    btn.textContent = '🔼 Скрыть фильтры';
                }}
            }}
            
            function clearFilters() {{
                document.querySelectorAll('input, select').forEach(el => {{
                    if (el.type === 'checkbox') el.checked = false;
                    else el.value = '';
                }});
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🔍 Расширенный поиск профилей</h1>
            
            <div class="messages">
    """
    
    # Добавляем сообщения
    if hasattr(request, '_messages'):
        for message in request._messages:
            html += f'<div class="message info">{message}</div>'
    
    html += f"""
            </div>
            
            <div class="filters-section">
                <div class="filters-toggle">
                    <button type="button" id="toggle-btn" class="btn" onclick="toggleFilters()">🔍 Показать фильтры</button>
                    <a href="/profiles/search/" class="btn btn-secondary">📋 Простой поиск</a>
                    <a href="/" class="btn btn-secondary">🏠 Главная</a>
                </div>
                
                <div id="filters-content" class="filters-content">
                    <form method="get" class="filters-form">
                        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
    """
    
    # Группируем поля формы по категориям
    field_groups = {
        'Основные параметры': ['gender', 'age_min', 'age_max', 'city'],
        'Физические данные': ['height_min', 'height_max', 'weight_min', 'weight_max', 'blood_group'],
        'Образование и карьера': ['education', 'employment'],
        'Образ жизни': ['smoking', 'alcohol', 'sport', 'health_rating_min', 'health_rating_max'],
        'Семейное положение': ['marital_status', 'orientation', 'has_children', 'has_diseases'],
        'Цель поиска': ['conception_method', 'father_contact', 'payment_approach'],
        'Поиск и настройки': ['search', 'with_photos_only', 'online_recently', 'sort_by']
    }
    
    for group_name, field_names in field_groups.items():
        html += f"""
                        <div class="filter-group">
                            <h4>{group_name}</h4>
        """
        
        for field_name in field_names:
            if field_name in form.fields:
                field = form.fields[field_name]
                field_value = form.data.get(field_name, '') if form.is_bound else ''
                
                # Обработка диапазонов (min/max)
                if field_name.endswith('_min') or field_name.endswith('_max'):
                    base_name = field_name.replace('_min', '').replace('_max', '')
                    if f'{base_name}_min' in field_names and f'{base_name}_max' in field_names:
                        # Если это первое поле диапазона, создаем группу
                        if field_name.endswith('_min'):
                            min_field = form.fields[f'{base_name}_min']
                            max_field = form.fields[f'{base_name}_max']
                            min_value = form.data.get(f'{base_name}_min', '') if form.is_bound else ''
                            max_value = form.data.get(f'{base_name}_max', '') if form.is_bound else ''
                            
                            html += f"""
                            <div class="form-row">
                                <div class="form-group">
                                    <label for="id_{base_name}_min">{min_field.label}:</label>
                                    <input type="number" id="id_{base_name}_min" name="{base_name}_min" value="{min_value}" class="form-control" placeholder="{min_field.widget.attrs.get('placeholder', '')}">
                                </div>
                                <div class="form-group">
                                    <label for="id_{base_name}_max">{max_field.label}:</label>
                                    <input type="number" id="id_{base_name}_max" name="{base_name}_max" value="{max_value}" class="form-control" placeholder="{max_field.widget.attrs.get('placeholder', '')}">
                                </div>
                            </div>
                            """
                        # Пропускаем max поле, так как оно уже обработано
                        continue
                
                html += f'<div class="form-group"><label for="id_{field_name}">{field.label}:</label>'
                
                # Чекбоксы для множественного выбора
                if hasattr(field.widget, 'choices') and isinstance(field.widget, forms.CheckboxSelectMultiple):
                    selected_values = form.data.getlist(field_name) if form.is_bound else []
                    html += '<div class="checkbox-list">'
                    for value, label in field.choices:
                        checked = 'checked' if str(value) in selected_values else ''
                        html += f'''
                            <label>
                                <input type="checkbox" name="{field_name}" value="{value}" {checked}>
                                {label}
                            </label>
                        '''
                    html += '</div>'
                
                # Обычные селекты
                elif hasattr(field, 'choices') and field.choices:
                    html += f'<select id="id_{field_name}" name="{field_name}" class="form-control">'
                    for value, label in field.choices:
                        selected = 'selected' if str(field_value) == str(value) else ''
                        html += f'<option value="{value}" {selected}>{label}</option>'
                    html += '</select>'
                
                # Чекбокс
                elif isinstance(field.widget, forms.CheckboxInput):
                    checked = 'checked' if field_value else ''
                    html += f'<input type="checkbox" id="id_{field_name}" name="{field_name}" class="form-check-input" {checked}>'
                
                # Обычное текстовое поле
                else:
                    input_type = 'number' if isinstance(field.widget, forms.NumberInput) else 'text'
                    placeholder = field.widget.attrs.get('placeholder', '')
                    html += f'<input type="{input_type}" id="id_{field_name}" name="{field_name}" value="{field_value}" class="form-control" placeholder="{placeholder}">'
                
                html += '</div>'
        
        html += '</div>'
    
    html += f"""
                        <div style="grid-column: 1 / -1; text-align: center; margin-top: 20px;">
                            <button type="submit" class="btn">🔍 Найти профили</button>
                            <button type="button" class="btn btn-clear" onclick="clearFilters()">🗑️ Очистить фильтры</button>
                        </div>
                    </form>
                </div>
            </div>
            
            <div class="results-header">
                <h2>Результаты поиска</h2>
                <div class="results-count">Найдено: {total_count} профилей (показано: {len(page_obj)})</div>
            </div>
    """
    
    if page_obj.object_list:
        html += '<div class="profiles-grid">'
        
        for profile in page_obj.object_list:
            gender_icon = "👨" if profile.gender == 'male' else "👩"
            last_online = profile.last_online.strftime('%d.%m.%Y %H:%M')
            
            # Получаем главную фотографию
            main_photo = profile.photos.filter(is_primary=True).first()
            photo_url = main_photo.image.url if main_photo and main_photo.image else None
            
            html += f"""
                <div class="profile-card">
                    <div class="profile-header">
                        <div class="profile-icon">{gender_icon}</div>
                        <div class="profile-name">{profile.nickname}</div>
                    </div>
            """
            
            # Добавляем фотографию если есть
            if photo_url:
                try:
                    html += f"""
                        <div class="profile-photo">
                            <img src="{photo_url}" alt="Фото {profile.nickname}" 
                                 style="width: 100%; height: 180px; object-fit: cover; border-radius: 8px; margin-bottom: 15px;"
                                 onerror="this.style.display='none';">
                        </div>
                    """
                except Exception:
                    pass
            
            html += f"""
                    <div class="profile-info"><strong>Возраст:</strong> {profile.age} лет</div>
                    <div class="profile-info"><strong>Город:</strong> {profile.get_city_display()}</div>
                    <div class="profile-info"><strong>Рост/Вес:</strong> {profile.height} см / {profile.weight} кг</div>
                    <div class="profile-info"><strong>Образование:</strong> {profile.get_education_display()}</div>
                    <div class="profile-info"><strong>Здоровье:</strong> {profile.health_rating}/10</div>
                    <div class="profile-info"><strong>Активность:</strong> {last_online}</div>
                    <div class="profile-goal">
                        "{profile.goal[:80]}{'...' if len(profile.goal) > 80 else ''}"
                    </div>
                    <div class="profile-actions">
                        <a href="/profiles/view/{profile.id}/" class="btn btn-small">👁️ Посмотреть</a>
                        <a href="/profiles/message/{profile.user.id}/" class="btn btn-small">💌 Написать</a>
                    </div>
                </div>
            """
        
        html += '</div>'
        
        if total_count > 100:
            html += f"""
            <div style="text-align: center; margin-top: 20px; padding: 15px; background: #fff3cd; border-radius: 5px;">
                <p><strong>Показано первых 100 профилей из {total_count}.</strong></p>
                <p>Используйте фильтры для уточнения поиска.</p>
            </div>
            """
    else:
        html += """
            <div class="no-results">
                <h3>😔 Профили не найдены</h3>
                <p>Попробуйте изменить параметры поиска или очистить фильтры.</p>
            </div>
        """
    
    # Добавляем пагинацию для расширенного поиска
    if page_obj.object_list and page_obj.has_other_pages():
        html += """
            <div class="pagination">
                <div class="pagination-info">
        """
        html += f"""
                    Страница {page_obj.number} из {page_obj.paginator.num_pages} 
                    ({page_obj.start_index()}-{page_obj.end_index()} из {total_count} профилей)
        """
        html += """
                </div>
                <div class="pagination-controls">
        """
        
        # Получаем GET параметры для сохранения фильтров
        get_params = request.GET.copy()
        if 'page' in get_params:
            del get_params['page']
        query_string = '&' + get_params.urlencode() if get_params else ''
        
        # Первая страница
        if page_obj.has_previous():
            html += f'<a href="?page=1{query_string}" class="btn btn-pagination">« Первая</a>'
            html += f'<a href="?page={page_obj.previous_page_number()}{query_string}" class="btn btn-pagination">‹ Предыдущая</a>'
        
        # Текущая страница и соседние
        start_page = max(1, page_obj.number - 2)
        end_page = min(page_obj.paginator.num_pages, page_obj.number + 2)
        
        for page_num in range(start_page, end_page + 1):
            if page_num == page_obj.number:
                html += f'<span class="btn btn-pagination btn-current">{page_num}</span>'
            else:
                html += f'<a href="?page={page_num}{query_string}" class="btn btn-pagination">{page_num}</a>'
        
        # Последняя страница
        if page_obj.has_next():
            html += f'<a href="?page={page_obj.next_page_number()}{query_string}" class="btn btn-pagination">Следующая ›</a>'
            html += f'<a href="?page={page_obj.paginator.num_pages}{query_string}" class="btn btn-pagination">Последняя »</a>'
        
        html += """
                </div>
            </div>
        """

    html += """
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html)
