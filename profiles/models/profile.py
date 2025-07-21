from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import os

from .base import user_photo_path, BaseManager, TimestampedModel, ActiveModel


class ProfileManager(BaseManager):
    """Оптимизированный менеджер для модели Profile"""
    
    def with_user(self):
        """Возвращает профили с предзагруженными пользователями"""
        return self.select_related('user')
    
    def with_photos(self):
        """Возвращает профили с предзагруженными фотографиями"""
        return self.prefetch_related('photos')
    
    def with_primary_photo(self):
        """Возвращает профили с предзагруженными основными фотографиями"""
        from .profile import Photo  # Локальный импорт для избежания циклических зависимостей
        return self.prefetch_related(
            models.Prefetch('photos', queryset=Photo.objects.filter(is_primary=True))
        )
    
    def exclude_user(self, user):
        """Исключает указанного пользователя"""
        return self.exclude(user=user)
    
    def search_optimized(self, exclude_user=None):
        """Оптимизированный queryset для поиска профилей"""
        from .profile import Photo  # Локальный импорт
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
            male=Count('id', filter=Q(gender=1)),
            female=Count('id', filter=Q(gender=2))
        )


class PhotoManager(BaseManager):
    """Оптимизированный менеджер для модели Photo"""
    
    def verified(self):
        """Возвращает только проверенные фотографии"""
        return self.filter(is_verified=True)
    
    def primary_first(self):
        """Сортирует фотографии: основные сначала"""
        return self.order_by('-is_primary', '-uploaded_at')


class Profile(TimestampedModel, ActiveModel):
    """Модель профиля пользователя"""
    
    # Выборы для полей
    GENDER_CHOICES = [
        (1, 'Мужской'),
        (2, 'Женский'),
    ]
    
    ORIENTATION_CHOICES = [
        (1, 'Традиционная'),
        (2, 'Нетрадиционная'),
        (3, 'Любая'),
    ]
    
    MARITAL_STATUS_CHOICES = [
        (1, 'Не в браке'),
        (2, 'В браке'),
        (3, 'Разведен'),
        (4, 'Вдовец'),
    ]
    
    EDUCATION_CHOICES = [
        (1, 'Высшее'),
        (2, 'Среднее'),
        (3, 'Среднее специальное'),
    ]
    
    EMPLOYMENT_CHOICES = [
        (1, 'Имею работу'),
        (2, 'Безработный'),
        (3, 'Студент'),
    ]
    
    SMOKING_CHOICES = [
        (1, 'Не курю'),
        (2, 'Курю'),
        (3, 'Бросил'),
    ]
    
    ALCOHOL_CHOICES = [
        (1, 'Не пью'),
        (2, 'Крайне редко'),
        (3, 'Умеренно'),
    ]
    
    SPORT_CHOICES = [
        (1, 'Занимаюсь'),
        (2, 'Не занимаюсь'),
        (3, 'Время от времени'),
    ]
    
    BLOOD_GROUP_CHOICES = [
        (1, 'I положительная'),
        (2, 'I отрицательная'),
        (3, 'II положительная'),
        (4, 'II отрицательная'),
        (5, 'III положительная'),
        (6, 'III отрицательная'),
        (7, 'IV положительная'),
        (8, 'IV отрицательная'),
    ]
    
    CONCEPTION_METHOD_CHOICES = [
        (1, 'По договоренности'),
        (2, 'Другое'),
    ]
    
    CONTACT_CHOICES = [
        (1, 'Не важно'),
        (2, 'Важно'),
    ]
    
    PAYMENT_CHOICES = [
        (1, 'Без оплаты'),
        (2, 'С оплатой'),
    ]
    
    APPEARANCE_CHOICES = [
        (1, 'Европейский светлый'),
        (2, 'Южно-европейский слегка смуглый'),
        (3, 'Смуглый азиатский'),
        (4, 'Желтый монголоидный'),
        (5, 'Латиноамериканский'),
        (6, 'Негроидный'),
    ]
    
    CITY_CHOICES = [
        (1, 'Москва'),
        (2, 'Санкт-Петербург'),
        (3, 'Новосибирск'),
        (4, 'Екатеринбург'),
        (5, 'Казань'),
        (6, 'Нижний Новгород'),
        (7, 'Челябинск'),
        (8, 'Самара'),
        (9, 'Омск'),
        (10, 'Ростов-на-Дону'),
        (11, 'Уфа'),
        (12, 'Красноярск'),
        (13, 'Воронеж'),
        (14, 'Пермь'),
        (15, 'Волгоград'),
    ]
    
    LOOKING_FOR_CHOICES = [
        (1, 'Женщин-натуралок'),
        (2, 'Женщин-лесбиянок'),
        (3, 'Пар женщина-женщина'),
        (4, 'Пар мужчина-женщина'),
        (5, 'Любых'),
    ]

    # Связь с пользователем
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Основная информация
    nickname = models.CharField('Ник', max_length=50)
    age = models.PositiveIntegerField('Возраст', validators=[MinValueValidator(18), MaxValueValidator(100)])
    height = models.PositiveIntegerField('Рост (см)', validators=[MinValueValidator(100), MaxValueValidator(250)])
    weight = models.PositiveIntegerField('Вес (кг)', validators=[MinValueValidator(30), MaxValueValidator(300)])
    blood_group = models.IntegerField('Группа крови', choices=BLOOD_GROUP_CHOICES)
    gender = models.IntegerField('Пол', choices=GENDER_CHOICES)
    city = models.IntegerField('Город', choices=CITY_CHOICES)
    
    # Личная информация
    orientation = models.IntegerField('Сексуальная ориентация', choices=ORIENTATION_CHOICES)
    marital_status = models.IntegerField('Семейное положение', choices=MARITAL_STATUS_CHOICES)
    goal = models.TextField('Цель поиска', default='Найти партнера для зачатия')
    education = models.IntegerField('Образование', choices=EDUCATION_CHOICES)
    employment = models.IntegerField('Занятость', choices=EMPLOYMENT_CHOICES)
    
    # Привычки и здоровье
    smoking = models.IntegerField('Отношение к курению', choices=SMOKING_CHOICES)
    alcohol = models.IntegerField('Отношение к алкоголю', choices=ALCOHOL_CHOICES)
    sport = models.IntegerField('Отношение к спорту', choices=SPORT_CHOICES)
    health_rating = models.PositiveIntegerField('Оценка здоровья', validators=[MinValueValidator(1), MaxValueValidator(10)])
    has_diseases = models.BooleanField('ВИЧ-инфекция, гепатит', default=False)
    
    # Представления о зачатии
    conception_method = models.IntegerField('Способ зачатия', choices=CONCEPTION_METHOD_CHOICES)
    father_contact = models.IntegerField('Контакт с ребенком', choices=CONTACT_CHOICES)
    payment_approach = models.IntegerField('Оплата', choices=PAYMENT_CHOICES)
    
    # Желаемые данные партнера
    looking_for = models.IntegerField('Ищу среди', choices=LOOKING_FOR_CHOICES)
    desired_age_min = models.PositiveIntegerField('Желаемый возраст от', null=True, blank=True)
    desired_age_max = models.PositiveIntegerField('Желаемый возраст до', null=True, blank=True)
    desired_height_min = models.PositiveIntegerField('Желаемый рост от', null=True, blank=True)
    desired_height_max = models.PositiveIntegerField('Желаемый рост до', null=True, blank=True)
    desired_weight_min = models.PositiveIntegerField('Желаемый вес от', null=True, blank=True)
    desired_weight_max = models.PositiveIntegerField('Желаемый вес до', null=True, blank=True)
    desired_appearance = models.IntegerField('Тип внешности', choices=APPEARANCE_CHOICES, null=True, blank=True)
    desired_city = models.IntegerField('Желаемый город', choices=CITY_CHOICES, null=True, blank=True)
    
    # Дополнительные параметры
    has_children = models.BooleanField('Наличие детей', default=False)
    photo_required = models.BooleanField('Обязательно с фотографией', default=False)
    
    # Служебные поля
    last_online = models.DateTimeField('Последний заход', default=timezone.now)

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


class Photo(TimestampedModel):
    """Модель фотографии профиля"""
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField('Фотография', upload_to=user_photo_path)
    is_primary = models.BooleanField('Основная фотография', default=False)
    is_verified = models.BooleanField('Проверена', default=False)

    # Менеджер
    objects = PhotoManager()

    class Meta:
        verbose_name = 'Фотография'
        verbose_name_plural = 'Фотографии'
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"Фото {self.profile.nickname} - {self.created_at.date()}"
    
    def delete(self, *args, **kwargs):
        """Удалить файл изображения при удалении объекта"""
        if self.image:
            if os.path.isfile(self.image.path):
                os.remove(self.image.path)
        super().delete(*args, **kwargs)
