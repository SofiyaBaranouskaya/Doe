from django import forms
from .models import User, Content, Video, FunFact, Challenge, ChitChatUserChoice, Schools
from django.contrib.auth.forms import UserCreationForm
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.forms import AuthenticationForm


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'phone_number', 'password1', 'password2')

class SchoolForm(forms.Form):
    school = forms.ModelChoiceField(
        queryset=Schools.objects.all(),
        label="Current school / Alma mater *",
        empty_label="Select school...",
        widget=forms.Select(attrs={'class': 'school-select'})
    )


class ContentAdminForm(forms.ModelForm):
    object_id = forms.ModelChoiceField(queryset=FunFact.objects.none(), required=False, label="Object")

    class Meta:
        model = Content
        fields = ['content_type', 'object_id']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Фильтруем только существующие модели
        self.fields['content_type'].queryset = ContentType.objects.filter(
            model__in=['video', 'funfact', 'challenge', 'chitchat', 'quiz']
        )

        if 'content_type' in self.data:
            try:
                content_type_id = self.data.get('content_type')
                if content_type_id:
                    content_type = ContentType.objects.get(id=content_type_id)
                    self.set_object_id_queryset(content_type)
            except (ContentType.DoesNotExist, ValueError):
                pass
        elif self.instance.pk and self.instance.content_type:
            self.set_object_id_queryset(self.instance.content_type)

    def set_object_id_queryset(self, content_type):
        model_class = content_type.model_class()
        if model_class:
            self.fields['object_id'].queryset = model_class._base_manager.all()
            if self.instance.object_id:
                try:
                    self.initial['object_id'] = model_class._base_manager.get(pk=self.instance.object_id)
                except model_class.DoesNotExist:
                    pass

    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('content_type')
        object_id = cleaned_data.get('object_id')

        # Если выбран content_type, но не выбран object_id - не вызываем ошибку
        if content_type and not object_id:
            # Можно либо разрешить создание без object_id, либо установить значение по умолчанию
            pass

        return cleaned_data

    def clean_object_id(self):
        object_id = self.cleaned_data.get('object_id')
        return object_id.id if object_id else None


class FunFactForm(forms.ModelForm):
    class Meta:
        model = FunFact
        fields = ['title', 'fact_description', 'photo', 'points']
        widgets = {
            'photo_base64': forms.TextInput(attrs={'readonly': 'readonly'})
        }


class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ['title', 'description', 'video_file', 'duration', 'points', 'poster_url']
        widgets = {
            'poster_base64': forms.TextInput(attrs={'readonly': 'readonly'})
        }


class ChitChatChoiceForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.option_pairs = kwargs.pop('option_pairs', [])
        super().__init__(*args, **kwargs)

        for i, pair in enumerate(self.option_pairs, start=1):
            self.fields[f'pair_{i}'] = forms.ChoiceField(
                choices=[(pair.option_1, pair.option_1), (pair.option_2, pair.option_2)],
                widget=forms.Select(attrs={'class': 'form-select'}),
                label=f"Пара {i}"
            )