from django.db import models
from django.contrib.auth.models import User

from .base import BaseManager, TimestampedModel


class Report(TimestampedModel):
    """Модель жалобы на пользователя"""
    REASON_CHOICES = [
        ('spam', 'Спам'),
        ('inappropriate', 'Неподобающее поведение'),
        ('fake_profile', 'Поддельный профиль'),
        ('harassment', 'Домогательства'),
        ('other', 'Другое'),
    ]
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_received')
    reason = models.CharField('Причина жалобы', max_length=20, choices=REASON_CHOICES)
    description = models.TextField('Описание', blank=True)
    is_resolved = models.BooleanField('Рассмотрена', default=False)

    class Meta:
        verbose_name = 'Жалоба'
        verbose_name_plural = 'Жалобы'
        ordering = ['-created_at']
        unique_together = ['reporter', 'reported_user']

    def __str__(self):
        return f"Жалоба от {self.reporter.username} на {self.reported_user.username}"
