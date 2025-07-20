"""
Утилиты кэширования для сайта знакомств
Предоставляет функции и декораторы для эффективного кэширования данных
"""

import hashlib
import json
from functools import wraps
from typing import Any, Optional, Dict, List

from django.core.cache import caches, cache
from django.core.cache.utils import make_template_fragment_key
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import QuerySet


class CacheManager:
    """Менеджер кэширования для различных типов данных"""
    
    def __init__(self):
        self.default_cache = cache
        self.profiles_cache = caches['profiles']
        self.search_cache = caches['search']
        self.messages_cache = caches['messages']
    
    def get_cache_key(self, key_type: str, identifier: str, **kwargs) -> str:
        """Генерирует стандартизированный ключ кэша"""
        prefix = getattr(settings, 'CACHE_KEY_PREFIX', 'dating_site')
        
        # Добавляем дополнительные параметры к ключу
        key_parts = [prefix, key_type, str(identifier)]
        
        if kwargs:
            # Сортируем kwargs для консистентности ключей
            sorted_kwargs = sorted(kwargs.items())
            kwargs_str = '_'.join(f"{k}-{v}" for k, v in sorted_kwargs)
            key_parts.append(kwargs_str)
        
        return ':'.join(key_parts)
    
    def hash_key(self, key: str) -> str:
        """Создает хэш ключа для длинных ключей"""
        return hashlib.md5(key.encode('utf-8')).hexdigest()


# Глобальный экземпляр менеджера кэша
cache_manager = CacheManager()


def cache_profile(timeout: int = 900):
    """
    Декоратор для кэширования профильных данных
    Args:
        timeout: время жизни кэша в секундах (по умолчанию 15 минут)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Создаем ключ на основе имени функции и аргументов
            key_data = f"{func.__name__}_{str(args)}_{str(sorted(kwargs.items()))}"
            cache_key = cache_manager.hash_key(key_data)
            
            # Пытаемся получить из кэша
            cached_result = cache_manager.profiles_cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Выполняем функцию и кэшируем результат
            result = func(*args, **kwargs)
            cache_manager.profiles_cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


def cache_search_results(timeout: int = 600):
    """
    Декоратор для кэширования результатов поиска
    Args:
        timeout: время жизни кэша в секундах (по умолчанию 10 минут)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Создаем ключ на основе имени функции и аргументов
            key_data = f"search_{func.__name__}_{str(args)}_{str(sorted(kwargs.items()))}"
            cache_key = cache_manager.hash_key(key_data)
            
            # Пытаемся получить из кэша
            cached_result = cache_manager.search_cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Выполняем функцию и кэшируем результат
            result = func(*args, **kwargs)
            cache_manager.search_cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


def cache_conversation_data(timeout: int = 180):
    """
    Декоратор для кэширования данных сообщений/переписок
    Args:
        timeout: время жизни кэша в секундах (по умолчанию 3 минуты)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key_data = f"msg_{func.__name__}_{str(args)}_{str(sorted(kwargs.items()))}"
            cache_key = cache_manager.hash_key(key_data)
            
            cached_result = cache_manager.messages_cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = func(*args, **kwargs)
            cache_manager.messages_cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


# ====================== СПЕЦИФИЧНЫЕ ФУНКЦИИ КЭШИРОВАНИЯ ======================

def get_cached_profile_stats() -> Dict[str, int]:
    """Получить кэшированную статистику профилей"""
    cache_key = cache_manager.get_cache_key('stats', 'profiles')
    cached_stats = cache_manager.profiles_cache.get(cache_key)
    
    if cached_stats is None:
        # Импортируем здесь, чтобы избежать циклических импортов
        from .models import Profile
        
        stats = Profile.objects.stats()
        cache_manager.profiles_cache.set(cache_key, stats, 600)  # 10 минут
        return stats
    
    return cached_stats


def get_cached_user_profile(user: User, use_cache: bool = True) -> Optional['Profile']:
    """
    Получить кэшированный профиль пользователя
    Args:
        user: экземпляр пользователя
        use_cache: использовать ли кэш
    """
    if not use_cache:
        from .models import Profile
        try:
            return Profile.objects.select_related('user').get(user=user)
        except Profile.DoesNotExist:
            return None
    
    cache_key = cache_manager.get_cache_key('profile', 'user', user_id=user.id)
    cached_profile = cache_manager.profiles_cache.get(cache_key)
    
    if cached_profile is None:
        from .models import Profile
        try:
            profile = Profile.objects.select_related('user').get(user=user)
            cache_manager.profiles_cache.set(cache_key, profile, 900)  # 15 минут
            return profile
        except Profile.DoesNotExist:
            # Кэшируем информацию об отсутствии профиля на короткое время
            cache_manager.profiles_cache.set(cache_key, 'NO_PROFILE', 60)
            return None
    
    return cached_profile if cached_profile != 'NO_PROFILE' else None


def invalidate_user_profile_cache(user: User):
    """Инвалидировать кэш профиля пользователя"""
    cache_key = cache_manager.get_cache_key('profile', 'user', user_id=user.id)
    cache_manager.profiles_cache.delete(cache_key)


def get_cached_recent_profiles(limit: int = 10) -> List['Profile']:
    """Получить кэшированный список новых профилей"""
    cache_key = cache_manager.get_cache_key('profiles', 'recent', limit=limit)
    cached_profiles = cache_manager.profiles_cache.get(cache_key)
    
    if cached_profiles is None:
        from .models import Profile
        
        profiles = list(Profile.objects.with_primary_photo()
                       .select_related('user')
                       .order_by('-created_at')[:limit])
        
        cache_manager.profiles_cache.set(cache_key, profiles, 300)  # 5 минут
        return profiles
    
    return cached_profiles


def cache_search_results_data(search_params: Dict, results: List, total_count: int, timeout: int = 600):
    """Кэшировать результаты поиска"""
    # Создаем стабильный ключ из параметров поиска
    search_key = json.dumps(search_params, sort_keys=True)
    cache_key = cache_manager.hash_key(f"search_results_{search_key}")
    
    cache_data = {
        'results': results,
        'total_count': total_count,
        'params': search_params
    }
    
    cache_manager.search_cache.set(cache_key, cache_data, timeout)


def get_cached_search_results(search_params: Dict) -> Optional[Dict]:
    """Получить кэшированные результаты поиска"""
    search_key = json.dumps(search_params, sort_keys=True)
    cache_key = cache_manager.hash_key(f"search_results_{search_key}")
    
    return cache_manager.search_cache.get(cache_key)


def invalidate_search_cache():
    """Инвалидировать весь кэш поиска"""
    cache_manager.search_cache.clear()


def get_cached_conversation_list(user: User) -> Optional[List]:
    """Получить кэшированный список переписок"""
    cache_key = cache_manager.get_cache_key('conversations', 'list', user_id=user.id)
    return cache_manager.messages_cache.get(cache_key)


def cache_conversation_list(user: User, conversations: List, timeout: int = 180):
    """Кэшировать список переписок"""
    cache_key = cache_manager.get_cache_key('conversations', 'list', user_id=user.id)
    cache_manager.messages_cache.set(cache_key, conversations, timeout)


def invalidate_conversation_cache(user: User):
    """Инвалидировать кэш переписок пользователя"""
    cache_key = cache_manager.get_cache_key('conversations', 'list', user_id=user.id)
    cache_manager.messages_cache.delete(cache_key)


def get_cached_unread_count(user: User) -> Optional[int]:
    """Получить кэшированное количество непрочитанных сообщений"""
    cache_key = cache_manager.get_cache_key('unread', 'count', user_id=user.id)
    return cache_manager.messages_cache.get(cache_key)


def cache_unread_count(user: User, count: int, timeout: int = 60):
    """Кэшировать количество непрочитанных сообщений"""
    cache_key = cache_manager.get_cache_key('unread', 'count', user_id=user.id)
    cache_manager.messages_cache.set(cache_key, count, timeout)


def invalidate_unread_count_cache(user: User):
    """Инвалидировать кэш непрочитанных сообщений"""
    cache_key = cache_manager.get_cache_key('unread', 'count', user_id=user.id)
    cache_manager.messages_cache.delete(cache_key)


# ====================== УТИЛИТЫ ДЛЯ МАССОВОЙ ИНВАЛИДАЦИИ ======================

def invalidate_all_profile_caches():
    """Инвалидировать все кэши профилей"""
    cache_manager.profiles_cache.clear()


def invalidate_all_caches():
    """Инвалидировать все кэши"""
    cache_manager.default_cache.clear()
    cache_manager.profiles_cache.clear()
    cache_manager.search_cache.clear()
    cache_manager.messages_cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Получить статистику использования кэша (если поддерживается)"""
    stats = {}
    
    # Для LocMemCache можем попытаться получить базовую информацию
    try:
        stats['default'] = {
            'backend': 'LocMemCache',
            'location': 'default-cache'
        }
        stats['profiles'] = {
            'backend': 'LocMemCache', 
            'location': 'profiles-cache'
        }
        stats['search'] = {
            'backend': 'LocMemCache',
            'location': 'search-cache'
        }
        stats['messages'] = {
            'backend': 'LocMemCache',
            'location': 'messages-cache'
        }
    except Exception as e:
        stats['error'] = str(e)
    
    return stats 