import os
import re
import mimetypes
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
import base64
from io import BytesIO
from PIL import Image
from django.utils.html import format_html
from django.utils.text import slugify

from apps.users.storage_backends import StorjVideoStorage
from utils.supabase_storage import SupabaseStorage
from django.utils.safestring import mark_safe


class User(AbstractUser):
    username = models.CharField(max_length=150, unique=True, blank=True)
    email = models.EmailField(unique=True)
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        max_length=500,
        storage=SupabaseStorage(bucket_name='profile_pictures'),  # без параметров
        blank=True,
        null=True
    )
    points_count = models.IntegerField(default=0)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    curr_city = models.CharField(max_length=70, blank=True, null=True)
    hometown = models.CharField(max_length=70, blank=True, null=True)
    current_vibe = models.CharField(max_length=255, blank=True, null=True)
    next_move = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    you_today = models.CharField(max_length=255, blank=True, null=True)

    completed_content = models.ManyToManyField(
        'Content',
        blank=True,
        related_name='completed_by'
    )

    def get_profile_picture_base64(self):
        try:
            if not self.profile_picture:
                return None

            img = Image.open(self.profile_picture)

            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background

            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            return base64.b64encode(buffered.getvalue()).decode('utf-8')

        except Exception as e:
            print(f"Error converting profile picture to Base64: {e}")
            return None

    def __str__(self):
        return self.username


class Invitation(models.Model):
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    invitee_email = models.EmailField()
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.inviter.email} invited {self.invitee_email}"

class UserReward(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='user_rewards')
    reward = models.ForeignKey('Rewards', on_delete=models.CASCADE)
    redeemed_at = models.DateTimeField(auto_now_add=True)
    points_spent = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.user.username} — {self.reward.title}"

class Schools(models.Model):
    name = models.CharField(max_length=70)
    code = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name = "Schools"
        verbose_name_plural = "Schools"

    def __str__(self):
        return self.name

class UserSchool(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='user_schools')
    school = models.ForeignKey('Schools', on_delete=models.SET_NULL, null=True, blank=True)
    other_school_name = models.CharField(max_length=150, blank=True, null=True)
    graduation_year = models.CharField(max_length=4)
    assigned_code = models.IntegerField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.school and not self.assigned_code:
            self.assigned_code = self.school.code
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.school or self.other_school_name} ({self.graduation_year})"




class Page(models.Model):
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)

    slug = models.SlugField(
        unique=True,
        editable=False
    )

    page_key = models.CharField(
        max_length=50,
        unique=True,
        editable=False
    )

    theme_color = models.CharField(
        max_length=20,
        default="#FD7981"
    )

    icon_svg = models.TextField(blank=True)

    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("order",)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

        if not self.page_key:
            self.page_key = slugify(self.title).replace("-", "_")

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title



class Content(models.Model):
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name="contents"
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name='Content type'
    )

    object_id = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    value = GenericForeignKey('content_type', 'object_id')

    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Display order',
        help_text='Order of display on the page'
    )

    poster_base64 = models.TextField(
        blank=True,
        null=True,
        editable=False,
        verbose_name='Poster url',
        help_text='Filled automatically for video content'
    )

    class Meta:
        ordering = ['page', 'order']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        if self.value:
            title = getattr(self.value, 'title', None) or str(self.value)
            return f'{self.value.__class__.__name__} "{title}"'
        return f'Content #{self.pk}'

    def save(self, *args, **kwargs):
        # автоматически проставляем order внутри страницы
        if not self.order:
            last_order = Content.objects.filter(
                page=self.page
            ).aggregate(
                models.Max('order')
            )['order__max'] or 0
            self.order = last_order + 1

        # если контент — видео, сохраняем постер
        if self.value and isinstance(self.value, Video):
            self.poster_base64 = getattr(self.value, 'poster_base64', None)

        super().save(*args, **kwargs)

    @property
    def poster_base64_display(self):
        if self.poster_base64:
            return f"data:image/jpeg;base64,{self.poster_base64}"
        return None

    class Meta:
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]
        ordering = ['page', 'order']  # сортируем по странице, затем по order


class Video(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    video_file = models.FileField(storage=StorjVideoStorage(), upload_to='')
    filename = models.CharField(max_length=200)
    poster_url = models.ImageField(
        upload_to='posters/',
        storage=SupabaseStorage(bucket_name='posters')
    )
    poster_base64 = models.TextField(blank=True, null=True)
    duration = models.CharField(max_length=20)
    points = models.PositiveIntegerField(default=50)

    def __str__(self):
        return self.title

    def clean(self):
        errors = {}
        if not self.title:
            errors['title'] = 'Title is required'
        if not self.description:
            errors['description'] = 'Description is required'
        if not self.video_file:
            errors['video_file'] = 'Video file is required'
        if self.points is None:
            errors['points'] = 'Points are required'
        if not self.duration:
            errors['duration'] = 'Duration is required'
        if not self.poster_url:
            self.poster_base64 = None

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.clean()

        # Авто-запись имени файла при загрузке
        if self.video_file and hasattr(self.video_file, 'name'):
            raw_name = os.path.basename(self.video_file.name)
            self.filename = raw_name.replace(' ', '_')

        # Попробуем сохранить полный URL
        if self.video_file and hasattr(self.video_file, 'url'):
            self.video_url = self.video_file.url

        if self.pk:
            old_video = Video.objects.get(pk=self.pk)
            if old_video.poster_url != self.poster_url or not self.poster_base64:
                self.convert_poster_to_base64()
        else:
            if self.poster_url:
                self.convert_poster_to_base64()

        super().save(*args, **kwargs)

    def convert_poster_to_base64(self):
        try:
            if not self.poster_url:
                self.poster_base64 = None
                return

            img = Image.open(self.poster_url)

            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background

            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            self.poster_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        except Exception as e:
            print(f"Error converting poster image to Base64: {e}")
            self.poster_base64 = None

    def get_storj_url(self):
        return f"https://link.storjshare.io/s/jx3blensqenp6hmoiz444ldnnrxq/videobucket/{self.filename}?wrap=0"


class FunFact(models.Model):
    title = models.CharField(max_length=255)
    fact_description = models.TextField()
    points = models.PositiveIntegerField(default=25)
    photo = models.ImageField(
        upload_to='photos/',
        storage=SupabaseStorage(bucket_name='photos'),
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp'])]
    )
    duration = models.CharField(max_length=20, blank=True, null=True)

    photo_base64 = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.photo and not self.photo_base64:
            self.convert_image_to_base64()
        super().save(*args, **kwargs)

    @property
    def formatted_description(self):
        text = self.fact_description
        text = text.replace('/n', '<br>')
        text = text.replace('\n', '<br>')
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'_(.*?)_', r'<em>\1</em>', text)
        return mark_safe(text)

    def convert_image_to_base64(self):
        try:
            img = Image.open(self.photo)

            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background

            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)

            self.photo_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        except Exception as e:
            print(f"Error converting image to Base64: {e}")
            self.photo_base64 = None


class ChitChat(models.Model):
    title = models.CharField(
        max_length=500,
        verbose_name="Title",
        help_text="Fill the title",
        default="Would you rather?"
    )
    points = models.PositiveIntegerField(default=100)
    duration = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = "Chit Chat"
        verbose_name_plural = "Chit Chats"

    def __str__(self):
        return self.title[:50]


class ChitChatOption(models.Model):
    title = models.ForeignKey(
        ChitChat,
        on_delete=models.CASCADE,
        related_name='options',
    )

    option_1 = models.CharField(
        max_length=200,
        verbose_name="Option 1"
    )
    option_2 = models.CharField(
        max_length=200,
        verbose_name="Option 2"
    )

    def has_options(self):
        return bool(self.option_1 or self.option_2)

    class Meta:
        verbose_name = "Options Table"
        verbose_name_plural = "Options Tables"

    def __str__(self):
        return f"Options for {self.title}"


class ChitChatUserChoice(models.Model):
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        verbose_name="User"
    )
    chit_chat = models.ForeignKey(
        'ChitChat',
        on_delete=models.CASCADE,
        verbose_name="ChitChat"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Chit Chat | User Choice"
        verbose_name_plural = "Chit Chat | User Choices"
        unique_together = ('user', 'chit_chat')

    def __str__(self):
        return f"{self.user.username} - {self.chit_chat.title}"


class ChitChatAnswer(models.Model):
    user_choice = models.ForeignKey(
        ChitChatUserChoice,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="User's ChitChat Choice"
    )
    option_pair = models.ForeignKey(
        ChitChatOption,
        on_delete=models.CASCADE,
        verbose_name="Option Pair"
    )
    answer = models.CharField(
        max_length=200,
        verbose_name="User's Answer"
    )

    class Meta:
        verbose_name = "Chit Chat | Single Answer"
        verbose_name_plural = "Chit Chat | Single Answers"

    def __str__(self):
        return f"{self.user_choice.user.username}: {self.answer}"


class Challenge(models.Model):
    title = models.CharField(max_length=255, verbose_name="Title")
    picture = models.FileField(upload_to='challenges/', storage=SupabaseStorage(bucket_name='challenges'), verbose_name="Picture")
    instructions = models.TextField(verbose_name="Instructions")
    points = models.IntegerField(verbose_name="Points", default=100)
    button_add_name = models.CharField(max_length=50, verbose_name="Button add name")
    button_view_name = models.CharField(max_length=50, verbose_name="Button view name")
    picture_base64 = models.TextField(blank=True, null=True)
    min_answers_required = models.PositiveIntegerField(default=1, verbose_name="Minimum number of answers required")
    duration = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.pk:
            old_obj = Challenge.objects.filter(pk=self.pk).first()
            if old_obj and old_obj.picture != self.picture:
                self.convert_image_to_base64()
        elif self.picture:
            self.convert_image_to_base64()

        super().save(*args, **kwargs)

    @property
    def formatted_description(self):
        text = self.instructions
        text = text.replace('/n', '<br>').replace('\n', '<br>')  # Обрабатываем оба варианта
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'_(.*?)_', r'<em>\1</em>', text)
        return mark_safe(text)

    def convert_image_to_base64(self):
        mime_type, encoding = mimetypes.guess_type(self.picture.name)
        self.picture_mime_type = mime_type

        if mime_type == 'image/svg+xml':
            self.picture_base64 = None  # не конвертируем SVG
            return

        try:
            self.picture.seek(0)  # на всякий случай
            img = Image.open(self.picture)

            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background

            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            self.picture_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        except Exception as e:
            print(f"Error converting Challenge image to Base64: {e}")
            self.picture_base64 = None


class ChallengeElement(models.Model):
    ELEMENT_CHOICES = [
        ('input', 'Input'),
        ('textarea', 'Multiline Input'),
        ('radio', 'Radio Buttons'),
        ('checkbox', 'Checkboxes'),
        ('date', 'Date Picker'),
        ('file', 'File Upload'),
    ]

    TYPE_CHOICES = [
        ('text', 'Text'),
        ('int', 'Integer'),
        ('float', 'Float'),
        ('date', 'Date'),
    ]

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='elements', verbose_name="Challenge")
    order = models.PositiveIntegerField(default=0, verbose_name="Display order")
    name = models.CharField(max_length=255, verbose_name="Element name")
    element = models.CharField(max_length=20, choices=ELEMENT_CHOICES, verbose_name="Element")
    field_type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name="Data type")
    value = models.TextField(blank=True, verbose_name="Value")
    add_other_option = models.BooleanField(default=False, verbose_name='Add variant "Other"')
    show_after_confirm = models.BooleanField(default=False, verbose_name="Show after condition is done")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} ({self.element})"

    def get_options(self):
        options = [opt.strip() for opt in self.value.split(",")] if self.value else []
        if self.element in ["radio", "checkbox"] and self.add_other_option:
            options.append("Other")
        return options


class ChallengeDisplaySettings(models.Model):
    DISPLAY_TYPE_CHOICES = [
        ('text', 'Text Blocks'),
        ('table', 'Table'),
        ('nothing', 'Nothing'),
    ]

    challenge = models.OneToOneField(Challenge, on_delete=models.CASCADE, related_name='display_settings')
    display_type = models.CharField(max_length=10, choices=DISPLAY_TYPE_CHOICES, default='text', verbose_name="Display type")
    auto_adjust_table = models.BooleanField(default=True, verbose_name="Auto adjust table size")
    cancel_edit_delete = models.BooleanField(default=False, verbose_name="Cancel/Edit/Delete entire challenge")  # Добавляем поле

    def __str__(self):
        return f"Display settings for: {self.challenge.title}"


class TextFieldDisplayOrder(models.Model):
    settings = models.ForeignKey(ChallengeDisplaySettings, on_delete=models.CASCADE, related_name='text_fields')
    element = models.ForeignKey(ChallengeElement, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']


class TableColumnSetting(models.Model):
    settings = models.ForeignKey(ChallengeDisplaySettings, on_delete=models.CASCADE, related_name='table_columns')
    order = models.PositiveIntegerField()
    title = models.CharField(max_length=255, verbose_name="Column title")
    element = models.ForeignKey(ChallengeElement, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Field to display")
    cancel_edit_delete = models.BooleanField(default=False, verbose_name="Cancel/Edit/Delete field")  # Новый чекбокс

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title




class ChallengeUserChoice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challenge_choices')
    challenge = models.ForeignKey('Challenge', on_delete=models.CASCADE, related_name='user_choices')
    created_at = models.DateTimeField(auto_now_add=True)
    is_done = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'challenge')  # 1 запись на пользователя и челендж
        verbose_name = "Challenge | User choice"
        verbose_name_plural = "Challenge | User choices"

    def __str__(self):
        return f"{self.user.username} — {self.challenge.title}"

class ChallengeUserAttempt(models.Model):
    choice = models.ForeignKey(ChallengeUserChoice, on_delete=models.CASCADE, related_name='attempts')
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_done = models.BooleanField(default=False)
    is_secondary = models.BooleanField(default=False)

    def __str__(self):
        return f"Attempt at {self.submitted_at:%Y-%m-%d %H:%M}"

class ChallengeUserAnswer(models.Model):
    attempt = models.ForeignKey(ChallengeUserAttempt, on_delete=models.CASCADE, related_name='answers')
    element = models.ForeignKey('ChallengeElement', on_delete=models.CASCADE)
    answer = models.TextField()
    file = models.FileField(storage=StorjVideoStorage(), upload_to='usersvideo')

    def __str__(self):
        if self.file:
            return f"{self.element.name} → {self.file.name}"
        return f"{self.element.name} → {self.answer}"






class Quiz(models.Model):
    title = models.CharField(max_length=150)
    duration = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = "Quizzes"
        verbose_name_plural = "Quizzes"

    def __str__(self):
        return self.title

    def total_points(self):
        return self.questions.aggregate(total=models.Sum('points'))['total'] or 0

    def questions_count(self):
        return self.questions.count()

QUESTION_TYPE_CHOICES = [
    ('input', 'Input'),
    ('multiple', 'Multiple Choice'),
    ('single', 'One Answer'),
]

class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
    text = models.TextField("Question Text")
    image = models.ImageField(upload_to='quiz_images/', storage=SupabaseStorage(bucket_name='quiz_images'), blank=True, null=True)
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES)
    choices = models.TextField(
        blank=True,
        help_text="Comma-separated options (only for multiple or one answer)"
    )
    correct_answers = models.TextField(
        help_text="Comma-separated correct answers (match options exactly)"
    )
    points = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.text[:50]

    @property
    def choice_list(self):
        return [c.strip() for c in self.choices.split(';')] if self.choices else []

    @property
    def correct_answers_list(self):
        return [a.strip() for a in self.correct_answers.split(',')] if self.correct_answers else []

    def check_answer(self, user_answer):
        if self.question_type == 'multiple':
            user_answers = [a.strip() for a in user_answer.split(',')]
            return set(user_answers) == set(self.correct_answers_list)
        else:
            return user_answer.strip() in self.correct_answers_list

    def image_preview(self):
        if self.image:
            return format_html('<img src="{}" width="100" />', self.image.url)
        return "-"
    image_preview.short_description = "Preview"


class QuizUserChoice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    points_awarded = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Quiz | User Choice"
        verbose_name_plural = "Quiz | User Choices"
        unique_together = ('user', 'quiz')

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title}"

class QuizAnswer(models.Model):
    quiz_user_choice = models.ForeignKey(QuizUserChoice, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    user_answer = models.TextField(default=' ')
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Answer for {self.question.text} by {self.quiz_user_choice.user.username}"


class Favourites(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="likes")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    created_at = models.DateTimeField(auto_now_add=True)
    poster_base64 = models.TextField(
        blank=True,
        null=True,
        editable=False,
        verbose_name="Poster Base64"
    )

    class Meta:
        unique_together = ('user', 'content_type', 'object_id')

    def save(self, *args, **kwargs):
        # Если объект — видео, берём Base64 постер
        if isinstance(self.content_object, Video) and getattr(self.content_object, 'poster_base64', None):
            self.poster_base64 = self.content_object.poster_base64
        else:
            self.poster_base64 = None

        super().save(*args, **kwargs)


class Rewards(models.Model):
    title = models.CharField(max_length=50)
    description = models.TextField(max_length=255)
    points_needed = models.PositiveIntegerField()

    def __str__(self):
        return self.title


class Glossary(models.Model):
    COLOR_CHOICES = [
        ("#FF7B7730", "#FF7B7730"),
        ("#FFC6D4",  "#FFC6D4"),
        ("#FF7B7763", "#FF7B7763"),
        ("#FFE37F63", "#FFE37F63"),
    ]

    category = models.CharField(
        max_length=100,
        verbose_name="Category"
    )

    term = models.CharField(
        max_length=100,
        verbose_name="Term"
    )

    explanation = models.TextField(
        verbose_name="Explanation"
    )

    color = models.CharField(
        max_length=10,
        choices=COLOR_CHOICES,
        verbose_name="Color"
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Display order",
        help_text="Defines in what order this item appears."
    )

    def __str__(self):
        return f"{self.term} ({self.category})"

    def save(self, *args, **kwargs):
        # Auto-assign next order number if not set
        if not self.order:
            last_order = Glossary.objects.aggregate(
                models.Max('order')
            )['order__max'] or 0
            self.order = last_order + 1

        super().save(*args, **kwargs)

    class Meta:
        ordering = ["order"]
        verbose_name = "Glossary"
        verbose_name_plural = "Glossary"