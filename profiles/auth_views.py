from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .forms_package import CustomUserRegistrationForm, CustomAuthenticationForm
from .models import Profile


def register_view(request):
    """Представление для регистрации нового пользователя"""
    if request.user.is_authenticated:
        return redirect('profiles:home')
    
    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST)
        if form.is_valid():
            # Создаем пользователя
            user = form.save()
            
            # Автоматически входим в систему после регистрации
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {username}! Регистрация прошла успешно.')
                
                # Перенаправляем на создание профиля
                return redirect('profiles:create_profile')
            else:
                messages.error(request, 'Ошибка при входе в систему.')
                return redirect('auth:login')
        else:
            messages.error(request, 'Ошибки в форме регистрации. Проверьте введенные данные.')
    else:
        form = CustomUserRegistrationForm()
    
    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    """Представление для входа пользователя"""
    if request.user.is_authenticated:
        return redirect('profiles:home')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {username}!')
                
                # Перенаправляем на страницу профилей или на указанную в next
                next_page = request.GET.get('next', 'profiles:home')
                return redirect(next_page)
            else:
                messages.error(request, 'Неверный логин или пароль.')
        else:
            messages.error(request, 'Ошибки в форме входа.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'auth/login.html', {'form': form})


@login_required
def logout_view(request):
    """Представление для выхода пользователя"""
    username = request.user.username
    logout(request)
    messages.success(request, f'До свидания, {username}! Вы успешно вышли из системы.')
    return redirect('profiles:home')
