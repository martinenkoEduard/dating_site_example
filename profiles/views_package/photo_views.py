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

from ..models import Profile, Photo
from ..forms import PhotoUploadForm, MultiplePhotoUploadForm




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
