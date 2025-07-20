from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse
from .forms import CustomUserRegistrationForm, CustomAuthenticationForm
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
    
    # Генерируем HTML для страницы регистрации
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Регистрация - Сайт знакомств</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
            .auth-container {{ background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); max-width: 400px; width: 100%; }}
            .auth-header {{ text-align: center; margin-bottom: 30px; }}
            .auth-header h1 {{ color: #333; margin: 0; font-size: 2em; }}
            .auth-header p {{ color: #666; margin-top: 10px; }}
            .form-group {{ margin-bottom: 20px; }}
            .form-group label {{ display: block; margin-bottom: 8px; color: #333; font-weight: bold; }}
            .form-control {{ width: 100%; padding: 12px; border: 2px solid #e1e1e1; border-radius: 8px; font-size: 16px; transition: border-color 0.3s; box-sizing: border-box; }}
            .form-control:focus {{ border-color: #667eea; outline: none; }}
            .btn {{ width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: transform 0.2s; }}
            .btn:hover {{ transform: translateY(-2px); }}
            .auth-links {{ text-align: center; margin-top: 20px; }}
            .auth-links a {{ color: #667eea; text-decoration: none; font-weight: bold; }}
            .auth-links a:hover {{ text-decoration: underline; }}
            .messages {{ margin-bottom: 20px; }}
            .message {{ padding: 12px; border-radius: 8px; margin-bottom: 10px; }}
            .message.success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .message.error {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
            .errorlist {{ list-style: none; padding: 0; margin: 5px 0; }}
            .errorlist li {{ color: #721c24; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="auth-container">
            <div class="auth-header">
                <h1>💕 Регистрация</h1>
                <p>Создайте аккаунт для поиска партнера</p>
            </div>
            
            <div class="messages">
    """
    
    # Добавляем сообщения
    if messages.get_messages(request):
        for message in messages.get_messages(request):
            message_class = 'success' if message.tags == 'success' else 'error'
            html += f'<div class="message {message_class}">{message}</div>'
    
    html += """
            </div>
            
            <form method="post">
    """
    
    # Добавляем CSRF токен (упрощенно)
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    html += f'<input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">'
    
    # Добавляем поля формы
    for field_name, field in form.fields.items():
        field_value = form.data.get(field_name, '') if form.is_bound else ''
        errors = form.errors.get(field_name, []) if form.is_bound else []
        
        html += f"""
                <div class="form-group">
                    <label for="id_{field_name}">{field.label}:</label>
                    <input type="{field.widget.input_type}" 
                           id="id_{field_name}" 
                           name="{field_name}" 
                           value="{field_value}"
                           class="form-control" 
                           placeholder="{field.widget.attrs.get('placeholder', '')}">
        """
        
        if errors:
            html += '<ul class="errorlist">'
            for error in errors:
                html += f'<li>{error}</li>'
            html += '</ul>'
        
        html += '</div>'
    
    html += """
                <button type="submit" class="btn">Зарегистрироваться</button>
            </form>
            
            <div class="auth-links">
                <p>Уже есть аккаунт? <a href="/auth/login/">Войти</a></p>
                <p><a href="/">На главную</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html)


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
    
    # Генерируем HTML для страницы входа
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Вход - Сайт знакомств</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
            .auth-container {{ background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); max-width: 400px; width: 100%; }}
            .auth-header {{ text-align: center; margin-bottom: 30px; }}
            .auth-header h1 {{ color: #333; margin: 0; font-size: 2em; }}
            .auth-header p {{ color: #666; margin-top: 10px; }}
            .form-group {{ margin-bottom: 20px; }}
            .form-group label {{ display: block; margin-bottom: 8px; color: #333; font-weight: bold; }}
            .form-control {{ width: 100%; padding: 12px; border: 2px solid #e1e1e1; border-radius: 8px; font-size: 16px; transition: border-color 0.3s; box-sizing: border-box; }}
            .form-control:focus {{ border-color: #667eea; outline: none; }}
            .btn {{ width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: transform 0.2s; }}
            .btn:hover {{ transform: translateY(-2px); }}
            .auth-links {{ text-align: center; margin-top: 20px; }}
            .auth-links a {{ color: #667eea; text-decoration: none; font-weight: bold; }}
            .auth-links a:hover {{ text-decoration: underline; }}
            .messages {{ margin-bottom: 20px; }}
            .message {{ padding: 12px; border-radius: 8px; margin-bottom: 10px; }}
            .message.success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .message.error {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
            .errorlist {{ list-style: none; padding: 0; margin: 5px 0; }}
            .errorlist li {{ color: #721c24; font-size: 14px; }}
            .test-accounts {{ background: #e2f3ff; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #0066cc; }}
            .test-accounts h4 {{ margin: 0 0 10px 0; color: #0066cc; }}
            .test-accounts p {{ margin: 5px 0; font-size: 14px; color: #555; }}
        </style>
    </head>
    <body>
        <div class="auth-container">
            <div class="auth-header">
                <h1>🔐 Вход</h1>
                <p>Войдите в свой аккаунт</p>
            </div>
            
            <div class="test-accounts">
                <h4>🧪 Тестовые аккаунты:</h4>
                <p><strong>Админ:</strong> admin / admin123</p>
                <p><strong>Мужчина:</strong> mikhail25 / test123</p>
                <p><strong>Женщина:</strong> elena23 / test123</p>
            </div>
            
            <div class="messages">
    """
    
    # Добавляем сообщения
    if messages.get_messages(request):
        for message in messages.get_messages(request):
            message_class = 'success' if message.tags == 'success' else 'error'
            html += f'<div class="message {message_class}">{message}</div>'
    
    html += """
            </div>
            
            <form method="post">
    """
    
    # Добавляем CSRF токен
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    html += f'<input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">'
    
    # Добавляем поля формы
    for field_name, field in form.fields.items():
        field_value = form.data.get(field_name, '') if form.is_bound else ''
        errors = form.errors.get(field_name, []) if form.is_bound else []
        input_type = 'password' if field_name == 'password' else 'text'
        
        html += f"""
                <div class="form-group">
                    <label for="id_{field_name}">{field.label}:</label>
                    <input type="{input_type}" 
                           id="id_{field_name}" 
                           name="{field_name}" 
                           value="{field_value}"
                           class="form-control" 
                           placeholder="{field.widget.attrs.get('placeholder', '')}">
        """
        
        if errors:
            html += '<ul class="errorlist">'
            for error in errors:
                html += f'<li>{error}</li>'
            html += '</ul>'
        
        html += '</div>'
    
    html += """
                <button type="submit" class="btn">Войти</button>
            </form>
            
            <div class="auth-links">
                <p>Нет аккаунта? <a href="/auth/register/">Зарегистрироваться</a></p>
                <p><a href="/">На главную</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html)


@login_required
def logout_view(request):
    """Представление для выхода пользователя"""
    username = request.user.username
    logout(request)
    messages.success(request, f'До свидания, {username}! Вы успешно вышли из системы.')
    return redirect('profiles:home') 