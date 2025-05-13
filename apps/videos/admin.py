from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from apps.users.forms import ContentAdminForm
import nested_admin
from django import forms
from apps.users.models import (
    User, Content, Video, FunFact,
    ChitChat, ChitChatOption, ChitChatUserChoice,
    Challenge, ChallengeElement, ChallengeUserAnswer, ChallengeUserChoice, ChitChatAnswer, ChallengeDisplaySettings,
    TextFieldDisplayOrder, TableColumnSetting, ChallengeUserAttempt, Schools, UserSchool, QuizQuestion, Quiz,
    QuizUserChoice, QuizAnswer, Regards, UserReward, Invitation)

class UserSchoolInline(admin.TabularInline):
    model = UserSchool
    extra = 1

class UserRewardInline(admin.TabularInline):
    model = UserReward
    extra = 0
    readonly_fields = ('redeemed_at',)
    fields = ('reward', 'points_spent', 'redeemed_at')

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'points_count')
    search_fields = ('username', 'email')
    inlines = [UserSchoolInline, UserRewardInline]
    exclude = ('groups', 'user_permissions')
    filter_horizontal = ('completed_content',)


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('inviter', 'invitee_email', 'invited_at', 'accepted')
    search_fields = ('inviter__email', 'invitee_email')
    list_filter = ('accepted', 'invited_at')

@admin.register(Schools)
class SchoolsAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    form = ContentAdminForm
    list_display = ('content_type', 'safe_linked_object')
    readonly_fields = ('poster_base64', 'safe_linked_object')
    fields = ['page', 'content_type', 'object_id', 'poster_base64', 'safe_linked_object']

    def safe_linked_object(self, obj):
        if not obj.content_type:
            return "No content type"

        try:
            model_class = obj.content_type.model_class()
            if not model_class:
                return f"Model {obj.content_type.model} not found"

            if obj.object_id:
                try:
                    related_obj = model_class._base_manager.get(pk=obj.object_id)
                    url = reverse(
                        f'admin:{related_obj._meta.app_label}_{related_obj._meta.model_name}_change',
                        args=[obj.object_id]
                    )
                    return format_html('<a href="{}">{}</a>', url, str(related_obj))
                except model_class.DoesNotExist:
                    return f"Object {obj.object_id} not found"
            return "No object_id"
        except Exception as e:
            return f"Error: {str(e)}"

    safe_linked_object.short_description = 'Linked Object'
    safe_linked_object.allow_tags = True


@admin.register(FunFact)
class FunFactAdmin(admin.ModelAdmin):
    list_display = ('title', 'points')
    search_fields = ('title', 'points')
    readonly_fields = ('photo_base64',)
    readonly_fields = ('photo_preview',)

    def get_readonly_fields(self, request, obj=None):
        return ('photo_base64',) + self.readonly_fields

    def photo_preview(self, obj):
        if obj.photo_base64:
            return mark_safe(f'<img src="data:image/jpeg;base64,{obj.photo_base64}" width="150" />')
        elif obj.photo:
            return mark_safe(f'<img src="{obj.photo.url}" width="150" />')
        return "No photo"

    photo_preview.short_description = 'Preview photo'


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'points')
    fields = [
        'title',
        'description',
        'video_file',
        'poster_url',
        'points',
        'duration',
        'poster_base64',
        'poster_preview'
    ]
    search_fields = ('title', 'points')
    readonly_fields = ('poster_preview', 'poster_base64')

    def get_readonly_fields(self, request, obj=None):
        return super().get_readonly_fields(request, obj) + ('poster_base64',)

    def poster_preview(self, obj):
        if obj.poster_base64:
            return mark_safe(f'<img src="data:image/jpeg;base64,{obj.poster_base64}" width="150" />')
        elif obj.poster_url:
            return mark_safe(f'<img src="{obj.poster_url.url}" width="150" />')
        return "No poster"

    poster_preview.short_description = 'Poster Preview'


class ChitChatOptionForm(forms.ModelForm):
    class Meta:
        model = ChitChatOption
        fields = '__all__'
        widgets = {
            'option_1': forms.TextInput(),
            'option_2': forms.TextInput(),
            # Add more widgets if you have more option fields
        }


class ChitChatOptionInline(admin.TabularInline):
    model = ChitChatOption
    extra = 1
    can_delete = True
    show_change_link = True
    fields = ('option_1', 'option_2')


@admin.register(ChitChat)
class ChitChatAdmin(admin.ModelAdmin):
    inlines = [ChitChatOptionInline]
    list_display = ('title', 'points')
    search_fields = ('title', 'points')


class ChitChatAnswerInline(admin.TabularInline):
    model = ChitChatAnswer
    extra = 0
    readonly_fields = ('option_pair',)
    fields = ('option_pair', 'answer')
    can_delete = False


@admin.register(ChitChatUserChoice)
class ChitChatUserChoiceAdmin(admin.ModelAdmin):
    list_display = ('user', 'chit_chat', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ChitChatAnswerInline]

    def get_fields(self, request, obj=None):
        return ['user', 'chit_chat', 'created_at', 'updated_at']


class ChallengeElementInline(nested_admin.NestedTabularInline):
    model = ChallengeElement
    extra = 1
    fields = ('order', 'name', 'element', 'field_type', 'value', 'show_after_confirm')


class TextFieldDisplayOrderInline(nested_admin.NestedTabularInline):
    model = TextFieldDisplayOrder
    extra = 0
    fields = ('order', 'element')

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'element' and hasattr(request, '_challenge_obj'):
            kwargs["queryset"] = ChallengeElement.objects.filter(challenge=request._challenge_obj)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class TableColumnSettingInline(nested_admin.NestedTabularInline):
    model = TableColumnSetting
    extra = 0
    fields = ('order', 'title', 'element')  # Упростили список полей

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'element' and hasattr(request, '_challenge_obj'):
            kwargs["queryset"] = ChallengeElement.objects.filter(challenge=request._challenge_obj)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ChallengeDisplaySettingsInline(nested_admin.NestedStackedInline):
    model = ChallengeDisplaySettings
    fk_name = 'challenge'
    can_delete = False
    verbose_name_plural = "Display settings"

    inlines = []


@admin.register(Challenge)
class ChallengeAdmin(nested_admin.NestedModelAdmin):
    list_display = ('title', 'points')
    readonly_fields = ('photo_preview', 'picture_base64')
    search_fields = ('title',)

    def get_inline_instances(self, request, obj=None):
        inline_instances = []

        if obj:
            request._challenge_obj = obj

        inline_instances.append(ChallengeElementInline(self.model, self.admin_site))

        # Динамичный inline для display settings
        class DynamicDisplaySettingsInline(ChallengeDisplaySettingsInline):
            pass

        if obj:
            display_settings = getattr(obj, 'display_settings', None)

            if display_settings:
                if display_settings.display_type == 'text':
                    DynamicDisplaySettingsInline.inlines = [TextFieldDisplayOrderInline]
                elif display_settings.display_type == 'table':
                    DynamicDisplaySettingsInline.inlines = [TableColumnSettingInline]
                else:
                    DynamicDisplaySettingsInline.inlines = []
            else:
                DynamicDisplaySettingsInline.inlines = []
        else:
            DynamicDisplaySettingsInline.inlines = []

        inline_instances.append(DynamicDisplaySettingsInline(self.model, self.admin_site))

        return inline_instances

    def photo_preview(self, obj):
        if obj.picture_base64:
            return mark_safe(f'<img src="data:image/jpeg;base64,{obj.picture_base64}" width="150" />')
        elif obj.picture:
            return mark_safe(f'<img src="{obj.picture.url}" width="150" />')
        return "No photo"

    photo_preview.short_description = 'Preview photo'


class ChallengeUserAnswerInline(nested_admin.NestedTabularInline):
    model = ChallengeUserAnswer
    extra = 0
    readonly_fields = ('element', 'answer')


class ChallengeUserAttemptInline(nested_admin.NestedStackedInline):
    model = ChallengeUserAttempt
    extra = 0
    readonly_fields = ('submitted_at', )
    fields = ('submitted_at', 'is_done', 'is_secondary')
    inlines = [ChallengeUserAnswerInline]

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        original_form_class = formset.form

        class CustomForm(original_form_class):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                if self.instance.is_secondary:
                    for field in self.fields.values():
                        field.widget.attrs['style'] = 'background-color: #f3e8ff; border-left: 4px solid purple;'

        formset.form = CustomForm
        return formset


@admin.register(ChallengeUserChoice)
class ChallengeUserChoiceAdmin(nested_admin.NestedModelAdmin):
    model = ChallengeUserChoice
    inlines = [ChallengeUserAttemptInline]
    list_display = ['user', 'challenge']
    search_fields = ['user__username', 'challenge__title']


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 1
    fields = ('text', 'image', 'image_preview', 'question_type', 'choices', 'correct_answers', 'points')
    readonly_fields = ('image_preview',)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        return formset


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    inlines = [QuizQuestionInline]
    list_display = ('title',)


class QuizAnswerInline(admin.TabularInline):
    model = QuizAnswer
    fields = ('question', 'user_answer', 'is_correct')
    extra = 1


@admin.register(QuizUserChoice)
class QuizUserChoiceAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'submitted_at')
    inlines = [QuizAnswerInline]


@admin.register(Regards)
class RegardsAdmin(admin.ModelAdmin):
    list_display = ('title', 'points_needed')
    search_fields = ('title', 'points_needed')