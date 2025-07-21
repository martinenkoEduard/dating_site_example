from django import forms


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
