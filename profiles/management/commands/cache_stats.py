"""
Django management команда для статистики кэширования
Использование: python manage.py cache_stats
"""

from django.core.management.base import BaseCommand
from django.core.cache import caches
from profiles.cache_utils import get_cache_stats, cache_manager


class Command(BaseCommand):
    help = 'Показать статистику использования кэширования'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистить все кэши после показа статистики',
        )
        parser.add_argument(
            '--cache',
            type=str,
            choices=['default', 'profiles', 'search', 'messages', 'all'],
            default='all',
            help='Показать статистику конкретного кэша',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('=== Статистика кэширования сайта знакомств ===\n')
        )

        # Получаем статистику кэша
        stats = get_cache_stats()
        
        if options['cache'] == 'all':
            # Показываем все кэши
            for cache_name, cache_info in stats.items():
                if cache_name != 'error':
                    self.show_cache_info(cache_name, cache_info)
        else:
            # Показываем конкретный кэш
            cache_name = options['cache']
            if cache_name in stats:
                self.show_cache_info(cache_name, stats[cache_name])
            else:
                self.stdout.write(
                    self.style.ERROR(f'Кэш "{cache_name}" не найден')
                )

        # Дополнительная информация о конфигурации
        self.stdout.write('\n=== Конфигурация кэширования ===')
        self.stdout.write(f'Backend: {stats.get("default", {}).get("backend", "Unknown")}')
        
        if 'error' in stats:
            self.stdout.write(
                self.style.ERROR(f'Ошибка получения статистики: {stats["error"]}')
            )

        # Очистка кэшей если запрошена
        if options['clear']:
            self.clear_caches(options['cache'])

    def show_cache_info(self, cache_name, cache_info):
        """Показать информацию о конкретном кэше"""
        self.stdout.write(f'\n📦 Кэш: {cache_name.upper()}')
        self.stdout.write(f'   Backend: {cache_info.get("backend", "Unknown")}')
        self.stdout.write(f'   Location: {cache_info.get("location", "Unknown")}')
        
        # Показываем конфигурацию из settings если доступна
        from django.conf import settings
        cache_config = getattr(settings, 'CACHES', {}).get(cache_name, {})
        if cache_config:
            timeout = cache_config.get('TIMEOUT', 'Не указан')
            max_entries = cache_config.get('OPTIONS', {}).get('MAX_ENTRIES', 'Не указан')
            self.stdout.write(f'   Timeout: {timeout} секунд')
            self.stdout.write(f'   Max Entries: {max_entries}')

    def clear_caches(self, cache_type):
        """Очистить кэши"""
        self.stdout.write('\n=== Очистка кэшей ===')
        
        if cache_type == 'all':
            cache_manager.default_cache.clear()
            cache_manager.profiles_cache.clear()
            cache_manager.search_cache.clear()
            cache_manager.messages_cache.clear()
            self.stdout.write(
                self.style.SUCCESS('✅ Все кэши очищены')
            )
        elif cache_type == 'default':
            cache_manager.default_cache.clear()
            self.stdout.write(
                self.style.SUCCESS('✅ Основной кэш очищен')
            )
        elif cache_type == 'profiles':
            cache_manager.profiles_cache.clear()
            self.stdout.write(
                self.style.SUCCESS('✅ Кэш профилей очищен')
            )
        elif cache_type == 'search':
            cache_manager.search_cache.clear()
            self.stdout.write(
                self.style.SUCCESS('✅ Кэш поиска очищен')
            )
        elif cache_type == 'messages':
            cache_manager.messages_cache.clear()
            self.stdout.write(
                self.style.SUCCESS('✅ Кэш сообщений очищен')
            ) 