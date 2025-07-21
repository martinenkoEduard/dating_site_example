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


# ====================== РАСШИРЕННЫЙ ПОИСК ПРОФИЛЕЙ ======================



# ====================== СИСТЕМА СООБЩЕНИЙ ======================



def get_user_profile(user, use_cache=True):
    """Получить профиль пользователя с кэшированием"""
    # Эта функция заменена на get_cached_user_profile из cache_utils.py
    return get_cached_user_profile(user, use_cache)


def invalidate_user_profile_cache(user):
    """Очистить кэш профиля пользователя"""
    # Эта функция заменена на функцию из cache_utils.py
    invalidate_user_profile_cache(user)
