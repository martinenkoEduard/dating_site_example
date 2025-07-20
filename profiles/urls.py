from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    # Главная страница
    path('', views.home, name='home'),
    
    # Управление профилем
    path('profiles/create/', views.create_profile, name='create_profile'),
    path('profiles/my/', views.my_profile, name='my_profile'),
    path('profiles/edit/', views.edit_profile, name='edit_profile'),
    path('profiles/view/<int:profile_id>/', views.view_profile, name='view_profile'),
    path('profiles/search/', views.search_profiles, name='search_profiles'),
    path('profiles/advanced-search/', views.advanced_search_profiles, name='advanced_search_profiles'),
    
    # Управление фотографиями
    path('profiles/photos/', views.manage_photos, name='manage_photos'),
    path('profiles/photos/upload/', views.upload_photo, name='upload_photo'),
    path('profiles/photos/upload-multiple/', views.upload_multiple_photos, name='upload_multiple_photos'),
    path('profiles/photos/delete/<int:photo_id>/', views.delete_photo, name='delete_photo'),
    path('profiles/photos/set-primary/<int:photo_id>/', views.set_primary_photo, name='set_primary_photo'),
    
    # Система сообщений
    path('profiles/conversations/', views.conversations_list, name='conversations_list'),
    path('profiles/conversations/<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('profiles/message/<int:user_id>/', views.start_conversation, name='start_conversation'),
    path('profiles/report/<int:user_id>/', views.report_user, name='report_user'),
] 