from django.contrib import admin
from .models import Profile, Photo, Conversation, Message, MessageLimit, Report


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('nickname', 'gender', 'age', 'city', 'last_online', 'is_active')
    list_filter = ('gender', 'city', 'is_active', 'education', 'employment')
    search_fields = ('nickname', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'last_online')
    ordering = ('-last_online',)


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('profile', 'is_primary', 'is_verified', 'uploaded_at')
    list_filter = ('is_primary', 'is_verified', 'uploaded_at')
    search_fields = ('profile__nickname', 'profile__user__username')
    ordering = ('-uploaded_at',)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('participant1', 'participant2', 'created_at', 'last_message_at')
    search_fields = ('participant1__username', 'participant2__username')
    ordering = ('-last_message_at',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'sent_at', 'is_read')
    list_filter = ('is_read', 'sent_at')
    search_fields = ('sender__username', 'receiver__username', 'content')
    readonly_fields = ('sent_at', 'read_at')
    ordering = ('-sent_at',)


@admin.register(MessageLimit)
class MessageLimitAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'unanswered_count', 'last_message_at', 'hour_reset_at')
    list_filter = ('unanswered_count', 'last_message_at')
    search_fields = ('sender__username', 'receiver__username')
    ordering = ('-last_message_at',)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'reported_user', 'reason', 'created_at', 'is_resolved')
    list_filter = ('reason', 'is_resolved', 'created_at')
    search_fields = ('reporter__username', 'reported_user__username')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
