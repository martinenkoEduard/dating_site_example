from django import forms
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from ..models import Photo
from .widgets import MultipleFileField


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
