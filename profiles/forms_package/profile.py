from django import forms
from ..models import Profile


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
