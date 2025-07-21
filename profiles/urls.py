from django.urls import path
from .views_package import profile_views
from .views_package import photo_views
from .views_package import message_views

app_name = 'profiles'

urlpatterns = [
    # Главная страница
    path('', profile_views.home, name='home'),
    
    # Управление профилем
    path('profiles/create/', profile_views.create_profile, name='create_profile'),
    path('profiles/my/', profile_views.my_profile, name='my_profile'),
    path('profiles/edit/', profile_views.edit_profile, name='edit_profile'),
    path('profiles/view/<int:profile_id>/', profile_views.view_profile, name='view_profile'),
    path('profiles/search/', profile_views.search_profiles, name='search_profiles'),
    # path('profiles/advanced-search/', profile_views.advanced_search_profiles, name='advanced_search_profiles'),
    
    # Управление фотографиями
    path('profiles/photos/', photo_views.manage_photos, name='manage_photos'),
    path('profiles/photos/upload/', photo_views.upload_photo, name='upload_photo'),
    path('profiles/photos/upload-multiple/', photo_views.upload_multiple_photos, name='upload_multiple_photos'),
    path('profiles/photos/delete/<int:photo_id>/', photo_views.delete_photo, name='delete_photo'),
    path('profiles/photos/set-primary/<int:photo_id>/', photo_views.set_primary_photo, name='set_primary_photo'),
    
    # Система сообщений
    path('profiles/conversations/', message_views.conversations_list, name='conversations_list'),
    path('profiles/conversations/<int:conversation_id>/', message_views.conversation_detail, name='conversation_detail'),
    path('profiles/message/<int:user_id>/', message_views.start_conversation, name='start_conversation'),
    path('profiles/report/<int:user_id>/', message_views.report_user, name='report_user'),
] 