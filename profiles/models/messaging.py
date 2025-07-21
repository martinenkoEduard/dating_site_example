from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from .base import BaseManager, TimestampedModel


class ConversationManager(BaseManager):
    """Оптимизированный менеджер для модели Conversation"""
    
    def with_participants(self):
        """Возвращает беседы с предзагруженными участниками"""
        return self.select_related('participant1', 'participant2')
    
    def for_user(self, user):
        """Возвращает беседы для указанного пользователя"""
        from django.db.models import Q
        return self.filter(Q(participant1=user) | Q(participant2=user))
    
    def with_last_message(self):
        """Возвращает беседы с предзагруженными последними сообщениями"""
        return self.prefetch_related(
            models.Prefetch(
                'messages',
                queryset=Message.objects.select_related('sender', 'receiver').order_by('-sent_at')[:1],
                to_attr='last_message_list'
            )
        )


class MessageManager(BaseManager):
    """Оптимизированный менеджер для модели Message"""
    
    def with_users(self):
        """Возвращает сообщения с предзагруженными пользователями"""
        return self.select_related('sender', 'receiver')
    
    def unread_for_user(self, user):
        """Возвращает непрочитанные сообщения для пользователя"""
        return self.filter(receiver=user, is_read=False)
    
    def in_conversation(self, conversation):
        """Возвращает сообщения в указанной беседе"""
        return self.filter(conversation=conversation).select_related('sender', 'receiver')


class Conversation(TimestampedModel):
    """Модель переписки между пользователями"""
    participant1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_participant1')
    participant2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_participant2')
    last_message_at = models.DateTimeField('Последнее сообщение', auto_now_add=True)

    # Менеджер
    objects = ConversationManager()

    class Meta:
        verbose_name = 'Переписка'
        verbose_name_plural = 'Переписки'
        ordering = ['-last_message_at']
        unique_together = ['participant1', 'participant2']

    def __str__(self):
        return f"Переписка {self.participant1.username} - {self.participant2.username}"
    
    def get_other_participant(self, user):
        """Получить собеседника для данного пользователя"""
        return self.participant2 if user == self.participant1 else self.participant1
    
    def update_last_message_time(self):
        """Обновить время последнего сообщения"""
        self.last_message_at = timezone.now()
        self.save(update_fields=['last_message_at'])


class Message(models.Model):
    """Модель сообщения"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField('Содержание сообщения')
    sent_at = models.DateTimeField('Время отправки', auto_now_add=True)
    is_read = models.BooleanField('Прочитано', default=False)
    read_at = models.DateTimeField('Время прочтения', null=True, blank=True)

    # Менеджер
    objects = MessageManager()

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['sent_at']

    def __str__(self):
        return f"Сообщение от {self.sender.username} к {self.receiver.username} - {self.sent_at.strftime('%d.%m.%Y %H:%M')}"
    
    def mark_as_read(self):
        """Отметить сообщение как прочитанное"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class MessageLimit(TimestampedModel):
    """Модель для отслеживания лимитов сообщений (антиспам)"""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_limits')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_limits')
    unanswered_count = models.PositiveIntegerField('Количество неотвеченных сообщений', default=0)
    last_message_at = models.DateTimeField('Время последнего сообщения', auto_now_add=True)
    hour_reset_at = models.DateTimeField('Время сброса часового лимита', auto_now_add=True)

    class Meta:
        verbose_name = 'Лимит сообщений'
        verbose_name_plural = 'Лимиты сообщений'
        unique_together = ['sender', 'receiver']

    def __str__(self):
        return f"Лимит {self.sender.username} -> {self.receiver.username}: {self.unanswered_count}/10"
    
    def can_send_message(self):
        """Проверить, может ли пользователь отправить сообщение"""
        now = timezone.now()
        
        # Если прошел час с момента последнего сброса, сбрасываем счетчик
        if (now - self.hour_reset_at).total_seconds() >= 3600:
            self.unanswered_count = 0
            self.hour_reset_at = now
            self.save()
        
        return self.unanswered_count < 10
    
    def increment_unanswered(self):
        """Увеличить счетчик неотвеченных сообщений"""
        self.unanswered_count += 1
        self.last_message_at = timezone.now()
        self.save()
    
    def reset_unanswered(self):
        """Сбросить счетчик неотвеченных сообщений (при получении ответа)"""
        self.unanswered_count = 0
        self.save()
