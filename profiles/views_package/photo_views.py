from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.management import call_command
from django.contrib.auth.models import User
from django.db.utils import OperationalError
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
from django.conf import settings
from django import forms
import os

from ..models import Profile, Photo
from ..forms_package import ProfileForm, ProfileSearchForm
from ..cache_utils import (
    get_cached_user_profile, invalidate_user_profile_cache,
    get_cached_profile_stats, get_cached_recent_profiles,
    invalidate_search_cache
)


@login_required
def manage_photos(request):
    """Управление фотографиями профиля"""
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        messages.info(request, 'Сначала создайте профиль!')
        return redirect('profiles:create_profile')
    
    # Исправлено: используем created_at вместо uploaded_at
    photos = profile.photos.all().order_by('-is_primary', '-created_at')
    
    # Статистика
    photos_count = photos.count()
    primary_photo = photos.filter(is_primary=True).first()
    
    context = {
        'profile': profile,
        'photos': photos,
        'photos_count': photos_count,
        'primary_photo': primary_photo,
        'has_primary': bool(primary_photo),
    }
    
    return render(request, 'profiles/photos/manage_photos.html', context)


@login_required
def upload_photo(request):
    """Загрузка одной фотографии"""
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        messages.error(request, 'Сначала создайте профиль!')
        return redirect('profiles:create_profile')
    
    if request.method == 'POST':
        # Здесь нужно будет создать форму PhotoUploadForm
        # Пока что простая обработка
        if 'image' in request.FILES:
            try:
                photo = Photo.objects.create(
                    profile=profile,
                    image=request.FILES['image'],
                    is_primary=(not profile.photos.exists()),
                    is_verified=True
                )
                messages.success(request, 'Фотография успешно загружена!')
                return redirect('profiles:manage_photos')
            except Exception as e:
                messages.error(request, f'Ошибка при загрузке фотографии: {str(e)}')
        else:
            messages.error(request, 'Выберите файл для загрузки.')
    
    context = {
        'title': 'Загрузка фотографии',
        'single': True,
        'profile': profile,
    }
    
    return render(request, 'profiles/photos/upload_photo.html', context)


@login_required
def upload_multiple_photos(request):
    """Загрузка нескольких фотографий"""
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        messages.error(request, 'Сначала создайте профиль!')
        return redirect('profiles:create_profile')
    
    if request.method == 'POST':
        files = request.FILES.getlist('images')
        if files:
            uploaded_count = 0
            
            for file in files:
                try:
                    photo = Photo.objects.create(
                        profile=profile,
                        image=file,
                        is_primary=(not profile.photos.exists() and uploaded_count == 0),
                        is_verified=True
                    )
                    uploaded_count += 1
                except Exception as e:
                    messages.warning(request, f'Не удалось загрузить файл "{file.name}": {str(e)}')
            
            if uploaded_count > 0:
                messages.success(request, f'Успешно загружено {uploaded_count} фотографий!')
            return redirect('profiles:manage_photos')
        else:
            messages.error(request, 'Выберите файлы для загрузки.')
    
    context = {
        'title': 'Загрузка нескольких фотографий',
        'single': False,
        'profile': profile,
    }
    
    return render(request, 'profiles/photos/upload_photo.html', context)


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
