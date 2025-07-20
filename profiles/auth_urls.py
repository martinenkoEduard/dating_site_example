from django.urls import path
from . import auth_views

app_name = 'auth'

urlpatterns = [
    path('register/', auth_views.register_view, name='register'),
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
] 