from django.db import models
from django.utils import timezone
import os


def user_photo_path(instance, filename):
    """Путь для загрузки фотографий пользователей"""
    return f'photos/user_{instance.profile.user.id}/{filename}'


class BaseManager(models.Manager):
    """Базовый менеджер с общими методами"""
    
    def active(self):
        """Возвращает только активные записи"""
        return self.filter(is_active=True)


class TimestampedModel(models.Model):
    """Абстрактная модель с временными метками"""
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        abstract = True


class ActiveModel(models.Model):
    """Абстрактная модель с полем активности"""
    is_active = models.BooleanField('Активен', default=True)
    
    class Meta:
        abstract = True
