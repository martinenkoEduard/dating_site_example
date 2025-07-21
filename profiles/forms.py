from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from .models import Profile, Photo


class CustomUserRegistrationForm(UserCreationForm):
    """Кастомная форма регистрации пользователя"""
    email = forms.EmailField(
        label='Email',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите email'
        })
    )
    first_name = forms.CharField(
        label='Имя',
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите имя'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'email', 'password1', 'password2')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавляем CSS классы к полям
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Введите логин'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Повторите пароль'
        })
        
        # Русифицируем поля
        self.fields['username'].label = 'Логин'
        self.fields['password1'].label = 'Пароль'
        self.fields['password2'].label = 'Подтверждение пароля'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """Кастомная форма входа"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавляем CSS классы
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Введите логин'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
        
        # Русифицируем поля
        self.fields['username'].label = 'Логин'
        self.fields['password'].label = 'Пароль'


class PhotoUploadForm(forms.ModelForm):
    """Форма для загрузки фотографий"""
    
    class Meta:
        model = Photo
        fields = ['image', 'is_primary']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'multiple': False
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'image': 'Фотография',
            'is_primary': 'Сделать основной фотографией'
        }

    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile', None)
        super().__init__(*args, **kwargs)
        
        # Если у профиля нет фотографий, автоматически делаем загружаемую основной
        if self.profile and not self.profile.photos.exists():
            self.fields['is_primary'].initial = True
            self.fields['is_primary'].widget.attrs['checked'] = True

    def clean_image(self):
        image = self.cleaned_data.get('image')
        
        if image:
            # Проверка размера файла (максимум 5MB)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError('Размер файла не должен превышать 5MB.')
            
            # Проверка формата файла
            if not image.content_type.startswith('image/'):
                raise ValidationError('Загружаемый файл должен быть изображением.')
            
            # Проверка расширения файла
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            file_extension = image.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise ValidationError('Поддерживаемые форматы: JPG, JPEG, PNG, GIF, WEBP.')
            
            # Проверка разрешения изображения
            try:
                width, height = get_image_dimensions(image)
                if width and height:
                    # Минимальное разрешение 200x200
                    if width < 200 or height < 200:
                        raise ValidationError('Минимальное разрешение изображения: 200x200 пикселей.')
                    
                    # Максимальное разрешение 4000x4000
                    if width > 4000 or height > 4000:
                        raise ValidationError('Максимальное разрешение изображения: 4000x4000 пикселей.')
            except Exception:
                raise ValidationError('Не удалось обработать изображение. Проверьте корректность файла.')
        
        return image

    def clean_is_primary(self):
        is_primary = self.cleaned_data.get('is_primary')
        
        # Если устанавливается основная фотография, проверяем лимиты
        if is_primary and self.profile:
            # Проверяем общее количество фотографий
            photos_count = self.profile.photos.count()
            if photos_count >= 10:  # Максимум 10 фотографий
                raise ValidationError('Максимальное количество фотографий: 10.')
        
        return is_primary

    def save(self, commit=True):
        photo = super().save(commit=False)
        
        if self.profile:
            photo.profile = self.profile
            
            # Если это основная фотография, убираем флаг у других
            if photo.is_primary:
                self.profile.photos.update(is_primary=False)
        
        if commit:
            photo.save()
        
        return photo


class MultipleFileInput(forms.ClearableFileInput):
    """Кастомный виджет для загрузки нескольких файлов"""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Поле для загрузки нескольких файлов"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class MultiplePhotoUploadForm(forms.Form):
    """Форма для загрузки нескольких фотографий одновременно"""
    
    images = MultipleFileField(
        label='Фотографии',
        help_text='Выберите до 5 фотографий одновременно (JPG, PNG, GIF, WEBP, максимум 5MB каждая)'
    )

    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile', None)
        super().__init__(*args, **kwargs)
        
        # Добавляем CSS класс к виджету
        self.fields['images'].widget.attrs.update({
            'class': 'form-control',
            'accept': 'image/*',
            'multiple': True
        })

    def clean_images(self):
        files = self.files.getlist('images')
        
        if not files:
            raise ValidationError('Выберите хотя бы одну фотографию.')
        
        # Проверка количества файлов
        if len(files) > 5:
            raise ValidationError('Можно загрузить максимум 5 фотографий за раз.')
        
        # Проверка общего лимита фотографий профиля
        if self.profile:
            current_photos = self.profile.photos.count()
            if current_photos + len(files) > 10:
                raise ValidationError(f'Превышен лимит фотографий. У вас уже {current_photos} фото, можно добавить ещё {10 - current_photos}.')
        
        # Валидация каждого файла
        for file in files:
            # Размер файла
            if file.size > 5 * 1024 * 1024:
                raise ValidationError(f'Файл "{file.name}" слишком большой (максимум 5MB).')
            
            # Тип файла
            if not file.content_type.startswith('image/'):
                raise ValidationError(f'Файл "{file.name}" не является изображением.')
            
            # Расширение файла
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            file_extension = file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise ValidationError(f'Файл "{file.name}" имеет неподдерживаемый формат.')
            
            # Разрешение изображения
            try:
                width, height = get_image_dimensions(file)
                if width and height:
                    if width < 200 or height < 200:
                        raise ValidationError(f'Изображение "{file.name}" слишком маленькое (минимум 200x200).')
                    if width > 4000 or height > 4000:
                        raise ValidationError(f'Изображение "{file.name}" слишком большое (максимум 4000x4000).')
            except Exception:
                raise ValidationError(f'Не удалось обработать изображение "{file.name}".')
        
        return files


class ProfileForm(forms.ModelForm):
    """Форма для создания и редактирования профиля"""
    
    class Meta:
        model = Profile
        fields = [
            'nickname', 'age', 'height', 'weight', 'blood_group', 'gender', 'city',
            'orientation', 'marital_status', 'goal', 'education', 'employment',
            'smoking', 'alcohol', 'sport', 'health_rating', 'has_diseases',
            'conception_method', 'father_contact', 'payment_approach',
            'looking_for', 'desired_age_min', 'desired_age_max',
            'desired_height_min', 'desired_height_max', 'desired_weight_min', 'desired_weight_max',
            'desired_appearance', 'desired_city', 'has_children', 'photo_required'
        ]
        
        widgets = {
            'nickname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите ваш ник'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'min': '18', 'max': '100'}),
            'height': forms.NumberInput(attrs={'class': 'form-control', 'min': '100', 'max': '250', 'placeholder': 'см'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'min': '30', 'max': '300', 'placeholder': 'кг'}),
            'blood_group': forms.Select(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'city': forms.Select(attrs={'class': 'form-control'}),
            'orientation': forms.Select(attrs={'class': 'form-control'}),
            'marital_status': forms.Select(attrs={'class': 'form-control'}),
            'goal': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Опишите вашу цель поиска'}),
            'education': forms.Select(attrs={'class': 'form-control'}),
            'employment': forms.Select(attrs={'class': 'form-control'}),
            'smoking': forms.Select(attrs={'class': 'form-control'}),
            'alcohol': forms.Select(attrs={'class': 'form-control'}),
            'sport': forms.Select(attrs={'class': 'form-control'}),
            'health_rating': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '10'}),
            'has_diseases': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'conception_method': forms.Select(attrs={'class': 'form-control'}),
            'father_contact': forms.Select(attrs={'class': 'form-control'}),
            'payment_approach': forms.Select(attrs={'class': 'form-control'}),
            'looking_for': forms.Select(attrs={'class': 'form-control'}),
            'desired_age_min': forms.NumberInput(attrs={'class': 'form-control', 'min': '18', 'max': '100'}),
            'desired_age_max': forms.NumberInput(attrs={'class': 'form-control', 'min': '18', 'max': '100'}),
            'desired_height_min': forms.NumberInput(attrs={'class': 'form-control', 'min': '100', 'max': '250'}),
            'desired_height_max': forms.NumberInput(attrs={'class': 'form-control', 'min': '100', 'max': '250'}),
            'desired_weight_min': forms.NumberInput(attrs={'class': 'form-control', 'min': '30', 'max': '300'}),
            'desired_weight_max': forms.NumberInput(attrs={'class': 'form-control', 'min': '30', 'max': '300'}),
            'desired_appearance': forms.Select(attrs={'class': 'form-control'}),
            'desired_city': forms.Select(attrs={'class': 'form-control'}),
            'has_children': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'photo_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
        labels = {
            'nickname': 'Ник',
            'age': 'Возраст',
            'height': 'Рост (см)',
            'weight': 'Вес (кг)',
            'blood_group': 'Группа крови',
            'gender': 'Пол',
            'city': 'Город',
            'orientation': 'Сексуальная ориентация',
            'marital_status': 'Семейное положение',
            'goal': 'Цель поиска',
            'education': 'Образование',
            'employment': 'Занятость',
            'smoking': 'Отношение к курению',
            'alcohol': 'Отношение к алкоголю',
            'sport': 'Отношение к спорту',
            'health_rating': 'Оценка здоровья (1-10)',
            'has_diseases': 'ВИЧ-инфекция, гепатит',
            'conception_method': 'Способ зачатия',
            'father_contact': 'Контакт с ребенком',
            'payment_approach': 'Оплата',
            'looking_for': 'Ищу среди',
            'desired_age_min': 'Желаемый возраст от',
            'desired_age_max': 'Желаемый возраст до',
            'desired_height_min': 'Желаемый рост от (см)',
            'desired_height_max': 'Желаемый рост до (см)',
            'desired_weight_min': 'Желаемый вес от (кг)',
            'desired_weight_max': 'Желаемый вес до (кг)',
            'desired_appearance': 'Тип внешности',
            'desired_city': 'Желаемый город',
            'has_children': 'Наличие детей',
            'photo_required': 'Обязательно с фотографией',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем некоторые поля необязательными для начального создания профиля
        self.fields['desired_age_min'].required = False
        self.fields['desired_age_max'].required = False
        self.fields['desired_height_min'].required = False
        self.fields['desired_height_max'].required = False
        self.fields['desired_weight_min'].required = False
        self.fields['desired_weight_max'].required = False
        self.fields['desired_appearance'].required = False
        self.fields['desired_city'].required = False

    def clean(self):
        cleaned_data = super().clean()
        
        # Валидация возрастных диапазонов
        age_min = cleaned_data.get('desired_age_min')
        age_max = cleaned_data.get('desired_age_max')
        if age_min and age_max and age_min > age_max:
            raise forms.ValidationError('Минимальный возраст не может быть больше максимального')
        
        # Валидация роста
        height_min = cleaned_data.get('desired_height_min')
        height_max = cleaned_data.get('desired_height_max')
        if height_min and height_max and height_min > height_max:
            raise forms.ValidationError('Минимальный рост не может быть больше максимального')
        
        # Валидация веса
        weight_min = cleaned_data.get('desired_weight_min')
        weight_max = cleaned_data.get('desired_weight_max')
        if weight_min and weight_max and weight_min > weight_max:
            raise forms.ValidationError('Минимальный вес не может быть больше максимального')
        
        return cleaned_data


class ProfileSearchForm(forms.Form):
    """Форма для поиска и фильтрации профилей"""
    
    # Основные фильтры
    gender = forms.ChoiceField(
        choices=[('', 'Любой пол')] + Profile.GENDER_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    age_min = forms.IntegerField(
        label='Возраст от',
        required=False,
        min_value=18,
        max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'От'})
    )
    
    age_max = forms.IntegerField(
        label='Возраст до',
        required=False,
        min_value=18,
        max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'До'})
    )
    
    city = forms.ChoiceField(
        choices=[('', 'Любой город')] + Profile.CITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    height_min = forms.IntegerField(
        label='Рост от (см)',
        required=False,
        min_value=100,
        max_value=250,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'От'})
    )
    
    height_max = forms.IntegerField(
        label='Рост до (см)',
        required=False,
        min_value=100,
        max_value=250,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'До'})
    )
    
    # Дополнительные фильтры
    education = forms.ChoiceField(
        choices=[('', 'Любое образование')] + Profile.EDUCATION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    employment = forms.ChoiceField(
        choices=[('', 'Любая занятость')] + Profile.EMPLOYMENT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    smoking = forms.ChoiceField(
        choices=[('', 'Любое отношение к курению')] + Profile.SMOKING_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    alcohol = forms.ChoiceField(
        choices=[('', 'Любое отношение к алкоголю')] + Profile.ALCOHOL_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # ИСПРАВЛЕННОЕ ПОЛЕ - используем строковые значения
    has_children = forms.ChoiceField(
        label='Наличие детей',
        choices=[
            ('', 'Не важно'),
            ('true', 'Есть дети'),
            ('false', 'Нет детей')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Поиск по ключевым словам
    search = forms.CharField(
        label='Поиск по нику или цели',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ник или ключевые слова'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        
        # Валидация возраста
        age_min = cleaned_data.get('age_min')
        age_max = cleaned_data.get('age_max')
        if age_min and age_max and age_min > age_max:
            raise forms.ValidationError('Минимальный возраст не может быть больше максимального')
        
        # Валидация роста
        height_min = cleaned_data.get('height_min')
        height_max = cleaned_data.get('height_max')
        if height_min and height_max and height_min > height_max:
            raise forms.ValidationError('Минимальный рост не может быть больше максимального')
        
        return cleaned_data



class AdvancedProfileSearchForm(forms.Form):
    """Расширенная форма для поиска и фильтрации профилей"""
    
    # ================ ОСНОВНЫЕ ФИЛЬТРЫ ================
    gender = forms.ChoiceField(
        label='Пол',
        choices=[('', 'Любой пол')] + Profile.GENDER_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    age_min = forms.IntegerField(
        label='Возраст от',
        required=False,
        min_value=18,
        max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'От'})
    )
    
    age_max = forms.IntegerField(
        label='Возраст до',
        required=False,
        min_value=18,
        max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'До'})
    )
    
    city = forms.MultipleChoiceField(
        label='Города',
        choices=Profile.CITY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'})
    )
    
    # ================ ФИЗИЧЕСКИЕ ПАРАМЕТРЫ ================
    height_min = forms.IntegerField(
        label='Рост от (см)',
        required=False,
        min_value=100,
        max_value=250,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'От'})
    )
    
    height_max = forms.IntegerField(
        label='Рост до (см)',
        required=False,
        min_value=100,
        max_value=250,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'До'})
    )
    
    weight_min = forms.IntegerField(
        label='Вес от (кг)',
        required=False,
        min_value=30,
        max_value=300,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'От'})
    )
    
    weight_max = forms.IntegerField(
        label='Вес до (кг)',
        required=False,
        min_value=30,
        max_value=300,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'До'})
    )
    
    blood_group = forms.MultipleChoiceField(
        label='Группа крови',
        choices=Profile.BLOOD_GROUP_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'})
    )
    
    # ================ ОБРАЗОВАНИЕ И КАРЬЕРА ================
    education = forms.MultipleChoiceField(
        label='Образование',
        choices=Profile.EDUCATION_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'})
    )
    
    employment = forms.MultipleChoiceField(
        label='Занятость',
        choices=Profile.EMPLOYMENT_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'})
    )
    
    # ================ ОБРАЗ ЖИЗНИ ================
    smoking = forms.MultipleChoiceField(
        label='Отношение к курению',
        choices=Profile.SMOKING_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'})
    )
    
    alcohol = forms.MultipleChoiceField(
        label='Отношение к алкоголю',
        choices=Profile.ALCOHOL_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'})
    )
    
    sport = forms.MultipleChoiceField(
        label='Отношение к спорту',
        choices=Profile.SPORT_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'})
    )
    
    health_rating_min = forms.IntegerField(
        label='Оценка здоровья от',
        required=False,
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'От 1'})
    )
    
    health_rating_max = forms.IntegerField(
        label='Оценка здоровья до',
        required=False,
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'До 10'})
    )
    
    # ================ СЕМЕЙНЫЕ ОТНОШЕНИЯ ================
    marital_status = forms.MultipleChoiceField(
        label='Семейное положение',
        choices=Profile.MARITAL_STATUS_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'})
    )
    
    orientation = forms.MultipleChoiceField(
        label='Ориентация',
        choices=Profile.ORIENTATION_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'})
    )
    
    has_children = forms.ChoiceField(
        label='Наличие детей',
        choices=[('', 'Не важно'), ('True', 'Есть дети'), ('False', 'Нет детей')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    has_diseases = forms.ChoiceField(
        label='Заболевания',
        choices=[('', 'Не важно'), ('True', 'Есть'), ('False', 'Нет')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # ================ ЦЕЛЬ ПОИСКА ================
    conception_method = forms.MultipleChoiceField(
        label='Способ зачатия',
        choices=Profile.CONCEPTION_METHOD_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'})
    )
    
    father_contact = forms.MultipleChoiceField(
        label='Контакт с ребенком',
        choices=Profile.CONTACT_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'})
    )
    
    payment_approach = forms.MultipleChoiceField(
        label='Подход к оплате',
        choices=Profile.PAYMENT_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'})
    )
    
    # ================ ПОИСК И СОРТИРОВКА ================
    search = forms.CharField(
        label='Поиск по тексту',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск по нику, цели или описанию'
        })
    )
    
    with_photos_only = forms.BooleanField(
        label='Только с фотографиями',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    online_recently = forms.ChoiceField(
        label='Активность',
        choices=[
            ('', 'Не важно'),
            ('24h', 'За последние 24 часа'),
            ('3d', 'За последние 3 дня'),
            ('week', 'За последнюю неделю'),
            ('month', 'За последний месяц')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sort_by = forms.ChoiceField(
        label='Сортировка',
        choices=[
            ('-last_online', 'По последней активности'),
            ('age', 'По возрасту (сначала молодые)'),
            ('-age', 'По возрасту (сначала старшие)'),
            ('height', 'По росту (по возрастанию)'),
            ('-height', 'По росту (по убыванию)'),
            ('created_at', 'По дате регистрации'),
            ('-health_rating', 'По оценке здоровья')
        ],
        required=False,
        initial='-last_online',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        
        # Валидация возраста
        age_min = cleaned_data.get('age_min')
        age_max = cleaned_data.get('age_max')
        if age_min and age_max and age_min > age_max:
            raise forms.ValidationError('Минимальный возраст не может быть больше максимального')
        
        # Валидация роста
        height_min = cleaned_data.get('height_min')
        height_max = cleaned_data.get('height_max')
        if height_min and height_max and height_min > height_max:
            raise forms.ValidationError('Минимальный рост не может быть больше максимального')
        
        # Валидация веса
        weight_min = cleaned_data.get('weight_min')
        weight_max = cleaned_data.get('weight_max')
        if weight_min and weight_max and weight_min > weight_max:
            raise forms.ValidationError('Минимальный вес не может быть больше максимального')
        
        # Валидация здоровья
        health_min = cleaned_data.get('health_rating_min')
        health_max = cleaned_data.get('health_rating_max')
        if health_min and health_max and health_min > health_max:
            raise forms.ValidationError('Минимальная оценка здоровья не может быть больше максимальной')
        
        return cleaned_data 


# ====================== ФОРМЫ СИСТЕМЫ СООБЩЕНИЙ ======================

class MessageForm(forms.Form):
    """Форма для отправки сообщения"""
    content = forms.CharField(
        label='Сообщение',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Введите ваше сообщение...',
            'maxlength': '1000'
        }),
        max_length=1000,
        min_length=10,
        help_text='Минимум 10 символов, максимум 1000 символов'
    )

    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()
        
        if not content:
            raise forms.ValidationError('Сообщение не может быть пустым.')
        
        if len(content) < 10:
            raise forms.ValidationError('Сообщение должно содержать минимум 10 символов.')
        
        # Проверка на спам (простые паттерны)
        spam_patterns = [
            'telegram', 'whatsapp', 'viber', 'skype',
            'www.', 'http', '.com', '.ru', '.net',
            'phone', 'телефон', 'номер', 'звони', 'звоните'
        ]
        
        content_lower = content.lower()
        for pattern in spam_patterns:
            if pattern in content_lower:
                raise forms.ValidationError(f'Сообщение содержит запрещенные элементы. Обменивайтесь контактами после знакомства.')
        
        # Проверка на повторяющиеся символы (антиспам)
        if len(set(content)) < len(content) * 0.3:  # Менее 30% уникальных символов
            raise forms.ValidationError('Сообщение содержит слишком много повторяющихся символов.')
        
        return content


class ReportForm(forms.Form):
    """Форма для подачи жалобы на пользователя"""
    REASON_CHOICES = [
        ('spam', 'Спам или навязчивые сообщения'),
        ('inappropriate', 'Неподобающее поведение'),
        ('fake_profile', 'Поддельный профиль'),
        ('harassment', 'Домогательства'),
        ('other', 'Другое'),
    ]
    
    reason = forms.ChoiceField(
        label='Причина жалобы',
        choices=REASON_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    description = forms.CharField(
        label='Дополнительные сведения',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Опишите проблему подробнее (необязательно)...'
        }),
        required=False,
        max_length=500
    )

    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        return description 