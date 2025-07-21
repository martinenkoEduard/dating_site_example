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
            male=Count('id', filter=Q(gender='male')),
            female=Count('id', filter=Q(gender='female'))
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
