from django import forms
from .models import User, Content, Video, FunFact, Challenge, ChitChatUserChoice, Schools
from django.contrib.auth.forms import UserCreationForm
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.forms import AuthenticationForm


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(required=True)

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("User with this email already exists")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
        return user

    class Meta:
        model = User
        fields = ('email', 'phone_number', 'password1', 'password2')


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
        fields = ['content_type', 'object_id', 'condition']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Фильтруем только существующие модели
        self.fields['content_type'].queryset = ContentType.objects.filter(
            model__in=['video', 'funfact', 'challenge', 'chitchat', 'quiz', 'staticimages']
        )

        # Настраиваем поле condition
        static_choices = [
            ('dob_before_1996', 'DOB: Before (or in) 1996'),
            ('dob_after_1996', 'DOB: After 1996'),
            ('grad_expected', 'Graduation Year: Expected this summer or later'),
            ('grad_already', 'Graduation Year: Already graduated'),
            ('vibe_early', 'Financial Knowledge vibe: I’m pretty new'),
            ('vibe_mid', 'Financial Knowledge vibe: Let’s call it “mid”'),
            ('vibe_expert', 'Financial Knowledge vibe: I’m the one that explains things to my friends'),
            ('industry_arts_design', 'Industry: Arts & Design'),
            ('industry_business', 'Industry: Business'),
            ('industry_communications_pr', 'Industry: Communications & PR'),
            ('industry_cs_tech', 'Industry: Computer Science & Technology'),
            ('industry_consulting', 'Industry: Consulting'),
            ('industry_data_science', 'Industry: Data Science & Analytics'),
            ('industry_education', 'Industry: Education'),
            ('industry_engineering', 'Industry: Engineering'),
            ('industry_environmental', 'Industry: Environmental / Sustainability'),
            ('industry_finance', 'Industry: Finance or Accounting'),
            ('industry_healthcare', 'Industry: Healthcare'),
            ('industry_hospitality', 'Industry: Hospitality / Tourism'),
            ('industry_ir', 'Industry: International Relations'),
            ('industry_journalism', 'Industry: Journalism'),
            ('industry_law', 'Industry: Law or Public Policy'),
            ('industry_marketing', 'Industry: Marketing or Advertising'),
            ('industry_media', 'Industry: Media & Entertainment'),
            ('industry_nonprofit', 'Industry: Non-Profit / Social Impact'),
            ('industry_psychology', 'Industry: Psychology or Behavioral Science'),
            ('industry_science', 'Industry: Science & Research'),
            ('industry_sports', 'Industry: Sports & Athletics'),
            ('industry_startups', 'Industry: Startups and Entrepreneurship'),
            ('industry_writing', 'Industry: Writing / Literature'),
        ]

        # Динамические школы
        schools = Schools.objects.all().order_by('name')
        for school in schools:
            static_choices.append((f'school_{school.id}', f'School: {school.name}'))

        self.fields['condition'] = forms.ChoiceField(
            choices=[('', '---------')] + static_choices,
            required=False,
            label='Access condition',
            help_text='Condition that must be met for this content to be available'
        )

        # Логика для object_id (как было раньше)
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

        if content_type and not object_id:
            pass  # Разрешаем создание без object_id

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