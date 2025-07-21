from django.contrib import admin
from .models import Profile, Photo, Conversation, Message, MessageLimit, Report


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('nickname', 'gender', 'age', 'city', 'last_online', 'is_active')
    list_filter = ('gender', 'city', 'is_active', 'education', 'employment')
    search_fields = ('nickname', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'last_online')
    ordering = ('-last_online',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'nickname', 'age', 'gender', 'city')
        }),
        ('Физические данные', {
            'fields': ('height', 'weight', 'blood_group')
        }),
        ('Личная информация', {
            'fields': ('orientation', 'marital_status', 'goal', 'education', 'employment')
        }),
        ('Здоровье и привычки', {
            'fields': ('smoking', 'alcohol', 'sport', 'health_rating', 'has_diseases')
        }),
        ('Предпочтения', {
            'fields': ('looking_for', 'desired_age_min', 'desired_age_max', 
                      'desired_height_min', 'desired_height_max',
                      'desired_weight_min', 'desired_weight_max',
                      'desired_appearance', 'desired_city')
        }),
        ('Дополнительно', {
            'fields': ('has_children', 'photo_required', 'is_active')
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at', 'last_online'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('profile', 'is_primary', 'is_verified', 'created_at')
    list_filter = ('is_primary', 'is_verified', 'created_at')
    search_fields = ('profile__nickname', 'profile__user__username')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('profile__user')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('participant1', 'participant2', 'created_at', 'last_message_at')
    search_fields = ('participant1__username', 'participant2__username')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-last_message_at',)
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('participant1', 'participant2')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'sent_at', 'is_read', 'content_preview')
    list_filter = ('is_read', 'sent_at')
    search_fields = ('sender__username', 'receiver__username', 'content')
    readonly_fields = ('sent_at', 'read_at')
    ordering = ('-sent_at',)
    
    def content_preview(self, obj):
        """Превью содержимого сообщения"""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Содержимое'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('sender', 'receiver', 'conversation')


@admin.register(MessageLimit)
class MessageLimitAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'unanswered_count', 'last_message_at', 'hour_reset_at')
    list_filter = ('unanswered_count', 'last_message_at')
    search_fields = ('sender__username', 'receiver__username')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-last_message_at',)
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('sender', 'receiver')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'reported_user', 'reason', 'created_at', 'is_resolved')
    list_filter = ('reason', 'is_resolved', 'created_at')
    search_fields = ('reporter__username', 'reported_user__username', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    actions = ['mark_as_resolved', 'mark_as_unresolved']
    
    def mark_as_resolved(self, request, queryset):
        """Отметить жалобы как рассмотренные"""
        updated = queryset.update(is_resolved=True)
        self.message_user(request, f'{updated} жалоб отмечено как рассмотренные.')
    mark_as_resolved.short_description = 'Отметить как рассмотренные'
    
    def mark_as_unresolved(self, request, queryset):
        """Отметить жалобы как нерассмотренные"""
        updated = queryset.update(is_resolved=False)
        self.message_user(request, f'{updated} жалоб отмечено как нерассмотренные.')
    mark_as_unresolved.short_description = 'Отметить как нерассмотренные'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('reporter', 'reported_user')


# Дополнительные настройки админки
admin.site.site_header = 'Администрирование сайта знакомств'
admin.site.site_title = 'Админ-панель'
admin.site.index_title = 'Добро пожаловать в админ-панель'
