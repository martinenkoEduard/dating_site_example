from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import os


def user_photo_path(instance, filename):
    """Путь для загрузки фотографий пользователей"""
    return f'photos/user_{instance.profile.user.id}/{filename}'


class ProfileManager(models.Manager):
    """Оптимизированный менеджер для модели Profile"""
    
    def with_user(self):
        """Возвращает профили с предзагруженными пользователями"""
        return self.select_related('user')
    
    def with_photos(self):
        """Возвращает профили с предзагруженными фотографиями"""
        return self.prefetch_related('photos')
    
    def with_primary_photo(self):
        """Возвращает профили с предзагруженными основными фотографиями"""
        return self.prefetch_related(
            models.Prefetch('photos', queryset=Photo.objects.filter(is_primary=True))
        )
    
    def active(self):
        """Возвращает только активные профили"""
        return self.filter(is_active=True)
    
    def exclude_user(self, user):
        """Исключает указанного пользователя"""
        return self.exclude(user=user)
    
    def search_optimized(self, exclude_user=None):
        """Оптимизированный queryset для поиска профилей"""
        qs = self.select_related('user').prefetch_related(
            models.Prefetch('photos', queryset=Photo.objects.filter(is_primary=True, is_verified=True))
        ).filter(is_active=True)
        
        if exclude_user:
            qs = qs.exclude(user=exclude_user)
            
        return qs.order_by('-last_online')
    
    def stats(self):
        """Возвращает статистику профилей (оптимизированный запрос)"""
        from django.db.models import Count, Q
        return self.aggregate(
            total=Count('id'),
            male=Count('id', filter=Q(gender='male')),
            female=Count('id', filter=Q(gender='female'))
        )


class PhotoManager(models.Manager):
    """Оптимизированный менеджер для модели Photo"""
    
    def verified(self):
        """Возвращает только проверенные фотографии"""
        return self.filter(is_verified=True)
    
    def primary_first(self):
        """Сортирует фотографии: основные сначала"""
        return self.order_by('-is_primary', '-uploaded_at')


class ConversationManager(models.Manager):
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


class MessageManager(models.Manager):
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


class Profile(models.Model):
    """Модель профиля пользователя"""
    
    # Выборы для полей
    GENDER_CHOICES = [
        ('male', 'Мужской'),
        ('female', 'Женский'),
    ]
    
    ORIENTATION_CHOICES = [
        ('traditional', 'Традиционная'),
        ('non_traditional', 'Нетрадиционная'),
        ('any', 'Любая'),
    ]
    
    MARITAL_STATUS_CHOICES = [
        ('single', 'Не в браке'),
        ('married', 'В браке'),
        ('divorced', 'Разведен'),
        ('widowed', 'Вдовец'),
    ]
    
    EDUCATION_CHOICES = [
        ('higher', 'Высшее'),
        ('secondary', 'Среднее'),
        ('specialized', 'Среднее специальное'),
    ]
    
    EMPLOYMENT_CHOICES = [
        ('employed', 'Имею работу'),
        ('unemployed', 'Безработный'),
        ('student', 'Студент'),
    ]
    
    SMOKING_CHOICES = [
        ('no', 'Не курю'),
        ('yes', 'Курю'),
        ('quit', 'Бросил'),
    ]
    
    ALCOHOL_CHOICES = [
        ('no', 'Не пью'),
        ('rarely', 'Крайне редко'),
        ('moderate', 'Умеренно'),
    ]
    
    SPORT_CHOICES = [
        ('active', 'Занимаюсь'),
        ('inactive', 'Не занимаюсь'),
        ('sometimes', 'Время от времени'),
    ]
    
    BLOOD_GROUP_CHOICES = [
        ('I+', 'I положительная'),
        ('I-', 'I отрицательная'),
        ('II+', 'II положительная'),
        ('II-', 'II отрицательная'),
        ('III+', 'III положительная'),
        ('III-', 'III отрицательная'),
        ('IV+', 'IV положительная'),
        ('IV-', 'IV отрицательная'),
    ]
    
    CONCEPTION_METHOD_CHOICES = [
        ('agreement', 'По договоренности'),
        ('other', 'Другое'),
    ]
    
    CONTACT_CHOICES = [
        ('not_important', 'Не важно'),
        ('important', 'Важно'),
    ]
    
    PAYMENT_CHOICES = [
        ('no_payment', 'Без оплаты'),
        ('with_payment', 'С оплатой'),
    ]
    
    APPEARANCE_CHOICES = [
        ('european_light', 'Европейский светлый'),
        ('south_european', 'Южно-европейский слегка смуглый'),
        ('swarthy_asian', 'Смуглый азиатский'),
        ('mongoloid', 'Желтый монголоидный'),
        ('latin_american', 'Латиноамериканский'),
        ('negroid', 'Негроидный'),
    ]
    
    CITY_CHOICES = [
        ('moscow', 'Москва'),
        ('spb', 'Санкт-Петербург'),
        ('novosibirsk', 'Новосибирск'),
        ('ekaterinburg', 'Екатеринбург'),
        ('kazan', 'Казань'),
        ('nizhny_novgorod', 'Нижний Новгород'),
        ('chelyabinsk', 'Челябинск'),
        ('samara', 'Самара'),
        ('omsk', 'Омск'),
        ('rostov_on_don', 'Ростов-на-Дону'),
        ('ufa', 'Уфа'),
        ('krasnoyarsk', 'Красноярск'),
        ('voronezh', 'Воронеж'),
        ('perm', 'Пермь'),
        ('volgograd', 'Волгоград'),
    ]
    
    LOOKING_FOR_CHOICES = [
        ('straight_women', 'Женщин-натуралок'),
        ('lesbian_women', 'Женщин-лесбиянок'),
        ('woman_woman_pairs', 'Пар женщина-женщина'),
        ('man_woman_pairs', 'Пар мужчина-женщина'),
        ('any', 'Любых'),
    ]

    # Связь с пользователем
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Основная информация
    nickname = models.CharField('Ник', max_length=50)
    age = models.PositiveIntegerField('Возраст', validators=[MinValueValidator(18), MaxValueValidator(100)])
    height = models.PositiveIntegerField('Рост (см)', validators=[MinValueValidator(100), MaxValueValidator(250)])
    weight = models.PositiveIntegerField('Вес (кг)', validators=[MinValueValidator(30), MaxValueValidator(300)])
    blood_group = models.CharField('Группа крови', max_length=10, choices=BLOOD_GROUP_CHOICES)
    gender = models.CharField('Пол', max_length=10, choices=GENDER_CHOICES)
    city = models.CharField('Город', max_length=50, choices=CITY_CHOICES)
    
    # Личная информация
    orientation = models.CharField('Сексуальная ориентация', max_length=20, choices=ORIENTATION_CHOICES)
    marital_status = models.CharField('Семейное положение', max_length=20, choices=MARITAL_STATUS_CHOICES)
    goal = models.TextField('Цель поиска', default='Найти партнера для зачатия')
    education = models.CharField('Образование', max_length=20, choices=EDUCATION_CHOICES)
    employment = models.CharField('Занятость', max_length=20, choices=EMPLOYMENT_CHOICES)
    
    # Привычки и здоровье
    smoking = models.CharField('Отношение к курению', max_length=10, choices=SMOKING_CHOICES)
    alcohol = models.CharField('Отношение к алкоголю', max_length=20, choices=ALCOHOL_CHOICES)
    sport = models.CharField('Отношение к спорту', max_length=20, choices=SPORT_CHOICES)
    health_rating = models.PositiveIntegerField('Оценка здоровья', validators=[MinValueValidator(1), MaxValueValidator(10)])
    has_diseases = models.BooleanField('ВИЧ-инфекция, гепатит', default=False)
    
    # Представления о зачатии
    conception_method = models.CharField('Способ зачатия', max_length=20, choices=CONCEPTION_METHOD_CHOICES)
    father_contact = models.CharField('Контакт с ребенком', max_length=20, choices=CONTACT_CHOICES)
    payment_approach = models.CharField('Оплата', max_length=20, choices=PAYMENT_CHOICES)
    
    # Желаемые данные партнера
    looking_for = models.CharField('Ищу среди', max_length=30, choices=LOOKING_FOR_CHOICES)
    desired_age_min = models.PositiveIntegerField('Желаемый возраст от', null=True, blank=True)
    desired_age_max = models.PositiveIntegerField('Желаемый возраст до', null=True, blank=True)
    desired_height_min = models.PositiveIntegerField('Желаемый рост от', null=True, blank=True)
    desired_height_max = models.PositiveIntegerField('Желаемый рост до', null=True, blank=True)
    desired_weight_min = models.PositiveIntegerField('Желаемый вес от', null=True, blank=True)
    desired_weight_max = models.PositiveIntegerField('Желаемый вес до', null=True, blank=True)
    desired_appearance = models.CharField('Тип внешности', max_length=30, choices=APPEARANCE_CHOICES, blank=True)
    desired_city = models.CharField('Желаемый город', max_length=50, choices=CITY_CHOICES, blank=True)
    
    # Дополнительные параметры
    has_children = models.BooleanField('Наличие детей', default=False)
    photo_required = models.BooleanField('Обязательно с фотографией', default=False)
    
    # Служебные поля
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    last_online = models.DateTimeField('Последний заход', default=timezone.now)
    is_active = models.BooleanField('Активен', default=True)

    # Менеджер
    objects = ProfileManager()

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'
        ordering = ['-last_online']

    def __str__(self):
        return f"{self.nickname} ({self.get_gender_display()}, {self.age} лет)"
    
    def update_last_online(self):
        """Обновить время последнего захода"""
        self.last_online = timezone.now()
        self.save(update_fields=['last_online'])


class Photo(models.Model):
    """Модель фотографии профиля"""
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField('Фотография', upload_to=user_photo_path)
    is_primary = models.BooleanField('Основная фотография', default=False)
    uploaded_at = models.DateTimeField('Дата загрузки', auto_now_add=True)
    is_verified = models.BooleanField('Проверена', default=False)

    # Менеджер
    objects = PhotoManager()

    class Meta:
        verbose_name = 'Фотография'
        verbose_name_plural = 'Фотографии'
        ordering = ['-is_primary', '-uploaded_at']

    def __str__(self):
        return f"Фото {self.profile.nickname} - {self.uploaded_at.date()}"
    
    def delete(self, *args, **kwargs):
        """Удалить файл изображения при удалении объекта"""
        if self.image:
            if os.path.isfile(self.image.path):
                os.remove(self.image.path)
        super().delete(*args, **kwargs)


class Conversation(models.Model):
    """Модель переписки между пользователями"""
    participant1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_participant1')
    participant2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_participant2')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
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


class MessageLimit(models.Model):
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


class Report(models.Model):
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
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    is_resolved = models.BooleanField('Рассмотрена', default=False)

    class Meta:
        verbose_name = 'Жалоба'
        verbose_name_plural = 'Жалобы'
        ordering = ['-created_at']
        unique_together = ['reporter', 'reported_user']

    def __str__(self):
        return f"Жалоба от {self.reporter.username} на {self.reported_user.username}"
