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
        form = PhotoUploadForm(request.POST, request.FILES, profile=profile)
        if form.is_valid():
            photo = form.save()
            messages.success(request, 'Фотография успешно загружена!')
            return redirect('profiles:manage_photos')
        else:
            messages.error(request, 'Ошибки при загрузке фотографии. Проверьте данные.')
    else:
        form = PhotoUploadForm(profile=profile)
    
    context = {
        'form': form,
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
        form = MultiplePhotoUploadForm(request.POST, request.FILES, profile=profile)
        if form.is_valid():
            files = form.cleaned_data['images']
            uploaded_count = 0
            
            for file in files:
                try:
                    photo = Photo.objects.create(
                        profile=profile,
                        image=file,
                        is_primary=(not profile.photos.exists()),
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
    
    context = {
        'form': form,
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
