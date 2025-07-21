from django import forms
from ..models import Profile


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
