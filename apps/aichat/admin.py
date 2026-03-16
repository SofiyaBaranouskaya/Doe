# apps/aichat/admin.py
from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.utils.timesince import timesince
import json
from .models import ChatSession, ChatMessage, UserFeedback


# 🔹 Inline для отображения сообщений внутри сессии
class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    can_delete = False
    readonly_fields = ['role', 'content_display', 'tokens_used', 'metadata_display', 'created_at']
    fields = ['role', 'content_display', 'tokens_used', 'created_at']

    def content_display(self, obj):
        text = obj.content[:200] + '...' if len(obj.content) > 200 else obj.content
        return format_html('<div style="max-width: 600px; white-space: pre-wrap;">{}</div>', text)

    content_display.short_description = 'Content'

    def metadata_display(self, obj):
        if obj.metadata:
            return format_html(
                '<pre style="background:#f5f5f5;padding:8px;border-radius:3px;font-size:11px;">{}</pre>',
                json.dumps(obj.metadata, indent=2, ensure_ascii=False)
            )
        return '—'

    metadata_display.short_description = 'Metadata'


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = [
        'session_id_short',
        'title',
        'user_link',
        'model_used',
        'message_count',
        'created_at',
        'updated_at_relative',
        'is_active',
    ]
    list_filter = ['is_active', 'model_used', 'created_at', 'updated_at']
    search_fields = ['session_id', 'title', 'user__username', 'user__email']
    readonly_fields = ['session_id', 'created_at', 'updated_at', 'message_count', 'context_display']
    fields = [
        'session_id', 'user', 'title', 'model_used',
        'is_active', 'context_display', 'created_at',
        'updated_at', 'message_count',
    ]
    inlines = [ChatMessageInline]  # 🔹 Показываем сообщения внутри сессии
    date_hierarchy = 'created_at'
    ordering = ['-updated_at']
    list_per_page = 50

    def session_id_short(self, obj):
        return obj.session_id[:12] + '...' if len(obj.session_id) > 12 else obj.session_id

    session_id_short.short_description = 'Session ID'

    def user_link(self, obj):
        if obj.user:
            url = f'/admin/auth/user/{obj.user.id}/change/'
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '— Anonymous —'

    user_link.short_description = 'User'

    def message_count(self, obj):
        return obj.get_message_count()

    message_count.short_description = 'Messages'

    def updated_at_relative(self, obj):
        return timesince(obj.updated_at) + ' ago'

    updated_at_relative.short_description = 'Last activity'

    def context_display(self, obj):
        if obj.context:
            return format_html(
                '<pre style="background:#f5f5f5;padding:10px;border-radius:5px;font-size:12px;overflow-x:auto;">{}</pre>',
                json.dumps(obj.context, indent=2, ensure_ascii=False)
            )
        return '—'

    context_display.short_description = 'Context'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = [
        'session_link',
        'role_badge',
        'content_preview',
        'tokens_used',
        'metadata_display',
        'has_feedback',
        'created_at_relative',
    ]
    list_filter = ['role', 'session__model_used', 'created_at']
    search_fields = ['content', 'session__session_id', 'session__title']
    readonly_fields = [
        'session', 'role', 'content_display', 'tokens_used',
        'metadata_display', 'created_at',
    ]
    fields = [
        'session', 'role', 'content_display', 'tokens_used',
        'metadata_display', 'created_at',
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 100

    def session_link(self, obj):
        url = f'/admin/aichat/chatsession/{obj.session.id}/change/'
        title = obj.session.title[:30] + '...' if len(obj.session.title) > 30 else obj.session.title
        return format_html('<a href="{}">{}</a>', url, title)

    session_link.short_description = 'Chat Session'

    def role_badge(self, obj):
        colors = {'user': '#3b82f6', 'assistant': '#22c55e', 'system': '#6b7280'}
        color = colors.get(obj.role, '#6b7280')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:10px;font-size:11px;">{}</span>',
            color, obj.role.upper()
        )

    role_badge.short_description = 'Role'

    def content_preview(self, obj):
        text = obj.content.replace('\n', ' ').strip()
        return text[:80] + '...' if len(text) > 80 else text

    content_preview.short_description = 'Content'

    # 🔹 ПОЛНОЕ ОТОБРАЖЕНИЕ CONTENT
    def content_display(self, obj):
        return format_html(
            '<div style="background:#f9f9f9;padding:15px;border-radius:5px;white-space:pre-wrap;font-family:monospace;font-size:13px;max-height:400px;overflow-y:auto;">{}</div>',
            obj.content
        )

    content_display.short_description = 'Full Content'

    def metadata_display(self, obj):
        if obj.metadata:
            return format_html(
                '<pre style="background:#f5f5f5;padding:10px;border-radius:5px;font-size:12px;overflow-x:auto;">{}</pre>',
                json.dumps(obj.metadata, indent=2, ensure_ascii=False)
            )
        return '—'

    metadata_display.short_description = 'Metadata'

    def has_feedback(self, obj):
        return '✅' if hasattr(obj, 'feedback') else '—'

    has_feedback.short_description = 'Feedback'

    def created_at_relative(self, obj):
        return timesince(obj.created_at) + ' ago'

    created_at_relative.short_description = 'Sent'


@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = [
        'message_link',
        'session_title',
        'rating_stars',
        'comment_preview',
        'created_at_relative',
    ]
    list_filter = ['rating', 'created_at', 'message__session__model_used']
    search_fields = ['comment', 'message__content', 'message__session__title']
    readonly_fields = ['message', 'rating', 'comment', 'created_at']
    fields = ['message', 'rating', 'comment', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 50

    def message_link(self, obj):
        url = f'/admin/aichat/chatmessage/{obj.message.id}/change/'
        preview = obj.message.content[:40] + '...' if len(obj.message.content) > 40 else obj.message.content
        return format_html('<a href="{}">{}</a>', url, preview)

    message_link.short_description = 'Message'

    def session_title(self, obj):
        return obj.message.session.title

    session_title.short_description = 'Chat Title'

    def rating_stars(self, obj):
        stars = '⭐' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span style="font-size:18px;">{}</span>', stars)

    rating_stars.short_description = 'Rating'

    def comment_preview(self, obj):
        if not obj.comment:
            return '—'
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment

    comment_preview.short_description = 'Comment'

    def created_at_relative(self, obj):
        return timesince(obj.created_at) + ' ago'

    created_at_relative.short_description = 'Received'


# Заголовки админки
admin.site.site_header = 'InvestPlatform Admin'
admin.site.site_title = 'InvestPlatform Dashboard'
admin.site.index_title = 'AI Chat Management'