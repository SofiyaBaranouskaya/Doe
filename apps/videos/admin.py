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
from import_export.admin import ExportMixin
from import_export import resources
from django.contrib.admin import SimpleListFilter
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

class UserResource(resources.ModelResource):
    class Meta:
        model = User

class ExportAdminMixin(ExportMixin, admin.ModelAdmin):
    pass

class UserSchoolInline(admin.TabularInline):
    model = UserSchool
    extra = 1

class UserRewardInline(admin.TabularInline):
    model = UserReward
    extra = 0
    readonly_fields = ('redeemed_at',)
    fields = ('reward', 'points_spent', 'redeemed_at')

class RewardFilter(admin.SimpleListFilter):
    title = _('Reward')
    parameter_name = 'reward'

    def lookups(self, request, model_admin):
        rewards = set(
            UserReward.objects.values_list('reward__id', 'reward__title')
        )
        return sorted(
            [r for r in rewards if r[1] is not None],
            key=lambda x: x[1]
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user_rewards__reward__id=self.value()).distinct()
        return queryset

class SchoolFilter(admin.SimpleListFilter):
    title = _('School')
    parameter_name = 'school'

    def lookups(self, request, model_admin):
        schools = set(
            UserSchool.objects.values_list('school__id', 'school__name')
        )
        # убираем None или подставляем пустую строку при сортировке
        filtered_schools = [s for s in schools if s[1] is not None]
        return sorted(filtered_schools, key=lambda x: x[1])

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user_schools__school__id=self.value()).distinct()
        return queryset

class SchoolCodeFilter(admin.SimpleListFilter):
    title = _('School code')
    parameter_name = 'school_code'

    def lookups(self, request, model_admin):
        codes = set(
            UserSchool.objects.values_list('assigned_code', 'assigned_code')
        )
        # Уберём None
        codes = filter(lambda x: x[0] is not None, codes)
        return sorted(codes, key=lambda x: x[0])

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user_schools__assigned_code=self.value()).distinct()
        return queryset

@admin.register(User)
class UserAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = UserResource
    list_display = ('username', 'email', 'points_count')
    search_fields = ('username', 'email')
    inlines = [UserSchoolInline, UserRewardInline]
    exclude = ('groups', 'user_permissions')
    filter_horizontal = ('completed_content',)
    list_filter = (
        'is_active',
        'date_joined',
        RewardFilter,
        SchoolFilter,
        SchoolCodeFilter,
    )

@admin.register(Invitation)
class InvitationAdmin(ExportAdminMixin):
    list_display = ('inviter', 'invitee_email', 'invited_at', 'accepted')
    search_fields = ('inviter__email', 'invitee_email')
    list_filter = ('accepted', 'invited_at')

@admin.register(Schools)
class SchoolsAdmin(ExportAdminMixin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


class SpecificContentTypeFilter(SimpleListFilter):
    title = 'content type'
    parameter_name = 'content_type'

    def lookups(self, request, model_admin):
        allowed_models = [Video, FunFact, Quiz, Challenge, ChitChat]
        lookups = []
        for model in allowed_models:
            ct = ContentType.objects.get_for_model(model)
            lookups.append((str(ct.id), model._meta.verbose_name))
        return lookups

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(content_type_id=self.value())
        return queryset

@admin.register(Content)
class ContentAdmin(ExportAdminMixin):
    form = ContentAdminForm
    list_display = ('content_type', 'safe_linked_object')
    readonly_fields = ('poster_base64', 'safe_linked_object')
    fields = ['page', 'content_type', 'object_id', 'poster_base64', 'safe_linked_object']
    list_filter = (SpecificContentTypeFilter, 'page')

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
class FunFactAdmin(ExportAdminMixin):
    list_display = ('title', 'points')
    search_fields = ('title', 'points')
    readonly_fields = ('photo_base64',)
    readonly_fields = ('photo_preview',)
    list_filter = ('points',)

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
class VideoAdmin(ExportAdminMixin):
    list_display = ('title', 'points')
    fields = (
        'title', 'description', 'video_file', 'poster_url',
        'duration', 'points', 'poster_preview', 'poster_base64'
    )
    search_fields = ('title', 'points')
    readonly_fields = ('poster_preview', 'poster_base64')
    list_filter = ('points',)

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
class ChitChatAdmin(ExportAdminMixin):
    inlines = [ChitChatOptionInline]
    list_display = ('title', 'points')
    search_fields = ('title', 'points')
    list_filter = ('points',)


class ChitChatAnswerInline(admin.TabularInline):
    model = ChitChatAnswer
    extra = 0
    readonly_fields = ('option_pair',)
    fields = ('option_pair', 'answer')
    can_delete = False


@admin.register(ChitChatUserChoice)
class ChitChatUserChoiceAdmin(ExportAdminMixin):
    list_display = ('user', 'chit_chat', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ChitChatAnswerInline]
    list_filter = ('created_at', 'chit_chat')

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

class ExportNestedAdmin(ExportMixin, nested_admin.NestedModelAdmin):
    pass

@admin.register(Challenge)
class ChallengeAdmin(ExportNestedAdmin):
    list_display = ('title', 'points')
    readonly_fields = ('photo_preview', 'picture_base64')
    search_fields = ('title',)
    list_filter = ('points',)

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
class ChallengeUserChoiceAdmin(ExportNestedAdmin):
    model = ChallengeUserChoice
    inlines = [ChallengeUserAttemptInline]
    list_display = ['user', 'challenge']
    search_fields = ['user__username', 'challenge__title']
    list_filter = ('challenge',)


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 1
    fields = ('text', 'image', 'image_preview', 'question_type', 'choices', 'correct_answers', 'points')
    readonly_fields = ('image_preview',)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        return formset


@admin.register(Quiz)
class QuizAdmin(ExportAdminMixin):
    inlines = [QuizQuestionInline]
    list_display = ('title',)


class QuizAnswerInline(admin.TabularInline):
    model = QuizAnswer
    fields = ('question', 'user_answer', 'is_correct')
    extra = 1


@admin.register(QuizUserChoice)
class QuizUserChoiceAdmin(ExportAdminMixin):
    list_display = ('user', 'quiz', 'submitted_at')
    inlines = [QuizAnswerInline]
    list_filter = ('submitted_at', 'quiz')

@admin.register(Regards)
class RegardsAdmin(ExportAdminMixin):
    list_display = ('title', 'points_needed')
    search_fields = ('title', 'points_needed')
    list_filter = ('points_needed',)
