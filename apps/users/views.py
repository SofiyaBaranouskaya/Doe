import os
from datetime import datetime
import json
import re

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .forms import RegistrationForm
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType
from .models import Video, FunFact, Content, Challenge, ChitChat, ChitChatOption, ChitChatUserChoice, \
    ChallengeUserAnswer, ChallengeUserChoice, ChitChatAnswer, ChallengeUserAttempt, Schools, UserSchool, Quiz, \
    QuizUserChoice, QuizAnswer, QuizQuestion, Regards, UserReward, Invitation
from django.contrib.auth import authenticate, login, get_backends
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth import get_user_model
from collections import defaultdict
from django.core.mail import send_mail
from django.conf import settings
from utils.supabase_upload import upload_user_avatar
from utils.generate_avatar import generate_initial_avatar
import logging


User = get_user_model()
logger = logging.getLogger(__name__)

def onboarding_view1(request):
    return render(request, 'users/onboarding1.html')

def onboarding_view2(request):
    return render(request, 'users/onboarding2.html')

def onboarding_view3(request):
    return render(request, 'users/onboarding3.html')

def onboarding_view4(request):
    return render(request, 'users/onboarding4.html')

def profile_end(request):
    return render(request, 'users/profile_end.html')

def google_oauth2_complete(request):
    """
    Обработчик завершения OAuth2 процесса (например, для Google).
    """
    user_email = request.GET.get('email')  # Получаем почту пользователя
    if user_email:
        try:
            # Ищем пользователя по email
            user = User.objects.get(email=user_email)
            # Логиним пользователя
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('home')  # Перенаправляем на домашнюю страницу
        except ObjectDoesNotExist:
            # Если пользователь не найден, создаём его
            messages.error(request, 'This account is not linked. Please sign up first.')
            return redirect('login')  # Перенаправляем на страницу логина
    else:
        # Если email не передан в запросе
        messages.error(request, 'Unable to retrieve email from OAuth2 provider.')
        return redirect('login')


def redirect_view(request):
    is_new_user = request.session.pop('is_new_user', False)
    if is_new_user:
        return redirect('profile')
    return redirect('home')


def user_profile(request):
    user = request.user
    rewards = Regards.objects.all()
    interests_list = []
    hobbies_list = []

    if user.interests:
        interests_list = [i.strip() for i in user.interests.split(',') if i.strip()]

    if user.hobbies:
        hobbies_list = [h.strip() for h in user.hobbies.split(',') if h.strip()]

    completed_count = user.completed_content.count()

    return render(request, 'videos/user_profile.html', {
        'user': user,
        'interests_list': interests_list,
        'hobbies_list': hobbies_list,
        'completed_count': completed_count,
        'rewards': rewards,
        'user_profile_picture_base64': user.get_profile_picture_base64(),
    })


def user_profile_change(request):
    user = request.user
    rewards = Regards.objects.all()
    interests_list = []
    hobbies_list = []
    schools = Schools.objects.all().order_by('name')

    user_schools = user.user_schools.select_related('school')

    if user.interests:
        interests_list = [i.strip() for i in user.interests.split(',') if i.strip()]

    if user.hobbies:
        hobbies_list = [h.strip() for h in user.hobbies.split(',') if h.strip()]

    completed_count = user.completed_content.count()

    return render(request, 'videos/user_profile_change.html', {
        'user': user,
        'interests_list': interests_list,
        'hobbies_json': json.dumps(hobbies_list),
        'completed_count': completed_count,
        'rewards': rewards,
        'schools': schools,
        'user_schools': user_schools,
    })



def get_user_points(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'points_count': request.user.points_count
        })
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def send_invite(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        data = json.loads(request.body)
        name = data.get('name')
        email = data.get('email')

        if not name or not email:
            return JsonResponse({'error': 'Missing fields'}, status=400)

        # Проверка: есть ли пользователь с такой почтой
        if User.objects.filter(email=email).exists():
            return JsonResponse({'message': 'This user is already using Doe'}, status=200)

        sender_email = request.user.email
        if not sender_email:
            return JsonResponse({'error': 'User email not found'}, status=400)

        # Формируем абсолютную ссылку на сайт
        base_url = request.build_absolute_uri('/')

        message = (
            f"{name}, congrats! You've been invited to Doe by {sender_email}!\n"
            f"Join us here: {base_url}"
        )

        send_mail(
            subject='Invitation to Doe',
            message=message,
            from_email=sender_email,
            recipient_list=[email],
            fail_silently=False,
        )

        return JsonResponse({'message': 'Invitation sent'})



@login_required
def redeem_reward(request):
    if request.method == 'POST':
        reward_id = request.POST.get('selected_reward')
        if not reward_id:
            return JsonResponse({
                'success': False,
                'error': 'Please select a reward'
            })

        reward = get_object_or_404(Regards, id=reward_id)
        user = request.user

        if user.points_count < reward.points_needed:
            return JsonResponse({
                'success': False,
                'error': 'Not enough points to redeem this reward'
            })

        # Создание записи о награде
        UserReward.objects.create(
            user=user,
            reward=reward,
            points_spent=reward.points_needed
        )

        # Списание баллов
        user.points_count -= reward.points_needed
        user.save()

        # Отправка email
        subject = f'New Reward Redeemed: {reward.title}'
        message = f'''
        User {user.email} redeemed reward:

        Reward: {reward.title}
        Points: {reward.points_needed}
        Date: {timezone.now().strftime("%Y-%m-%d %H:%M")}
        '''
        recipient_list = [os.getenv('DEFAULT_FROM_EMAIL')]

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list,
                fail_silently=False
            )
        except Exception as e:
            print(f"Email sending error: {str(e)}")

        return JsonResponse({
            'success': True,
            'message': f'You have successfully redeemed "{reward.title}"!',
            'new_points': user.points_count
        })

    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })


def signup_complete(request):
    return render(request, 'users/signup_complete.html')

def ajax_password_reset(request):
    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(
                request=request,
                use_https=request.is_secure(),
                email_template_name="registration/password_reset_email.html",
            )
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "error": "Invalid email address."})
    return JsonResponse({"success": False, "error": "Invalid request method."})


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()

            # Ищем приглашение
            invitation = Invitation.objects.filter(invitee_email=user.email, accepted=False).first()
            if invitation:
                # Помечаем как принято
                invitation.accepted = True
                invitation.save()

                # Начисляем баллы
                user.points_count += 100
                inviter = User.objects.filter(email=invitation.inviter.email).first()
                if inviter:
                    inviter.points_count += 150
                    inviter.save()
                user.save()

                # Отправляем письмо уведомление
                send_mail(
                    subject='User has registered',
                    message=f"{invitation.inviter.email} invited {user.email} to Doe (she signed up)!",
                    from_email='doe@gmail.com',  # лучше указать фиксированный адрес
                    recipient_list = [os.getenv('DEFAULT_FROM_EMAIL')],
                    fail_silently=False,
                )

            # логиним пользователя
            backend = get_backends()[0]
            user.backend = f"{backend.__module__}.{backend.__class__.__name__}"
            login(request, user)
            return redirect('signup_complete')
    else:
        form = RegistrationForm()

    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('username')
        password = request.POST.get('password')

        user = User.objects.filter(Q(email=identifier) | Q(phone_number=identifier)).first()
        if user:
            user = authenticate(request, username=user.username, password=password)
            if user:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, 'Incorrect password.')
        else:
            messages.error(request, 'User with this email or phone number did not exist.')

    return render(request, 'users/login.html')


def profile_view(request):
    schools = Schools.objects.all()
    return render(request, 'users/profile.html', {'schools': schools})


def parse_school_data(post_data):
    schools_data = defaultdict(dict)
    for key, value in post_data.items():
        if key.startswith("schools["):
            try:
                index = int(key.split('[')[1].split(']')[0])
                field = key.split('[')[2].split(']')[0]
                schools_data[index][field] = value
            except (IndexError, ValueError):
                continue
    return list(schools_data.values())


@login_required
def save_profile_steps(request):
    if request.method == 'POST':
        user = request.user

        # Update basic user info
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')

        # Handle date of birth
        dob_str = request.POST.get('dob')
        if dob_str:
            try:
                user.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                # Обработка неверного формата даты
                pass

        # Handle profile picture
        avatar_set = False
        # Для загруженного файла
        if 'avatar' in request.FILES:
            avatar_file = request.FILES['avatar']
            public_url = upload_user_avatar(
                file=avatar_file,
                user_id=user.id,
                file_name=avatar_file.name,
                content_type=avatar_file.content_type
            )
            if public_url:
                user.profile_picture_url = public_url
                avatar_set = True

        # Для сгенерированного аватара
        if not avatar_set and not user.profile_picture_url:
            generated_buffer = generate_initial_avatar(user)
            if generated_buffer:
                public_url = upload_user_avatar(
                    file=generated_buffer,
                    user_id=user.id,
                    file_name=f"avatar_{user.id}.png",
                    content_type='image/png'
                )
                if public_url:
                    user.profile_picture_url = public_url
                generated_buffer.close()

        # Parse JSON-like strings and convert to comma-separated
        interests_raw = request.POST.get('chosenIndustries', '[]')
        hobbies_raw = request.POST.get('chosenHobbies', '[]')

        try:
            interests_list = json.loads(interests_raw)
        except json.JSONDecodeError:
            interests_list = []

        try:
            hobbies_list = json.loads(hobbies_raw)
        except json.JSONDecodeError:
            hobbies_list = []

        user.focus_of_study = request.POST.get('majors', '')
        user.interests = ', '.join(interests_list)
        user.hobbies = ', '.join(hobbies_list)
        user.languages = request.POST.get('languages', '')
        user.motivation = request.POST.get('motivation', '')
        user.cities = request.POST.get('cities', '')
        user.current_focus = request.POST.get('current_focus', '')
        user.favorite_media = request.POST.get('fav_media', '')

        # Handle schools
        UserSchool.objects.filter(user=user).delete()
        school_entries = parse_school_data(request.POST)

        for entry in school_entries:
            school_id = entry.get('school_id')
            grad_year = entry.get('grad_year')
            other_name = entry.get('other_name', '')

            if school_id == '0' and other_name:
                # Создаем запись с пользовательским названием школы
                UserSchool.objects.create(
                    user=user,
                    school=None,
                    graduation_year=grad_year,
                    other_school_name=other_name
                )
            else:
                try:
                    school = Schools.objects.get(id=school_id)
                    UserSchool.objects.create(
                        user=user,
                        school=school,
                        graduation_year=grad_year
                    )
                except Schools.DoesNotExist:
                    # Школа не найдена, пропускаем
                    continue

        user.save()
        return redirect('home')

    return render(request, 'users/profile.html')

def generate_initial_avatar(user):
    from PIL import Image, ImageDraw, ImageFont
    import io
    import random
    from django.core.files.base import ContentFile

    # Генерируем случайный цвет фона
    bg_color = (
        random.randint(50, 200),
        random.randint(50, 200),
        random.randint(50, 200)
    )

    # Создаем изображение 200x200
    img_size = 200
    image = Image.new('RGB', (img_size, img_size), bg_color)
    draw = ImageDraw.Draw(image)

    # Получаем инициалы
    first_initial = user.first_name[0].upper() if user.first_name else 'U'
    last_initial = user.last_name[0].upper() if user.last_name else 'U'
    initials = f"{first_initial}{last_initial}"

    try:
        # Пробуем использовать шрифт Arial, если доступен
        font = ImageFont.truetype("arial.ttf", 80)
    except:
        # Используем стандартный шрифт, если Arial не найден
        font = ImageFont.load_default()

    # НОВЫЙ СПОСОБ РАСЧЕТА РАЗМЕРА ТЕКСТА (для Pillow 9.0.0+)
    # Получаем ограничивающий прямоугольник для текста
    left, top, right, bottom = draw.textbbox((0, 0), initials, font=font)
    text_width = right - left
    text_height = bottom - top

    # Рассчитываем положение текста
    position = ((img_size - text_width) // 2, (img_size - text_height) // 2)

    # Рисуем белый текст
    draw.text(position, initials, font=font, fill=(255, 255, 255))

    # Сохраняем изображение в памяти
    img_io = io.BytesIO()
    image.save(img_io, format='PNG')
    img_io.seek(0)

    # Создаем уникальное имя файла
    from django.utils.text import slugify
    import datetime
    filename = f"avatar_{slugify(user.username)}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.png"

    # Сохраняем аватар
    user.profile_picture.save(filename, ContentFile(img_io.getvalue()), save=False)

# def social_auth_error(request):
#     exception = request.GET.get('message', '')
#     if "already in use" in exception:
#         messages.warning(request, "This Google-account is already connected with another doe account. Plase, log in.")
#     return redirect('login')

def home_view(request):
    progress_data = {
        'money_talks': {'completed': 10, 'total': 100},
        'reach_girl': {'completed': 30, 'total': 100},
        'you_do_you': {'completed': 12, 'total': 100},
        'levers': {'completed': 13, 'total': 100},
        'portfolio': {'completed': 10, 'total': 100},
    }
    return render(request, 'videos/home_page.html')


def welcome_video(request):
    return render(request, 'videos/welcome_video.html')


def reach_girl_page(request):
    # Получаем все ContentType одним запросом
    content_types = ContentType.objects.filter(
        model__in=['video', 'funfact', 'challenge', 'chitchat', 'quiz']
    )

    # Получаем все содержимое с предварительной выборкой
    contents = Content.objects.filter(
        content_type__in=content_types,
        page='rich_girl'
    ).select_related('content_type').order_by('id')

    # Создаем словарь для группировки объектов по типам
    from collections import defaultdict
    objects_by_type = defaultdict(list)

    for content in contents:
        objects_by_type[content.content_type.model].append(content.object_id)

    # Получаем все объекты одним запросом для каждого типа
    videos = Video.objects.in_bulk(objects_by_type.get('video', []))
    funfacts = FunFact.objects.in_bulk(objects_by_type.get('funfact', []))
    challenges = Challenge.objects.in_bulk(objects_by_type.get('challenge', []))
    chitchats = ChitChat.objects.in_bulk(objects_by_type.get('chitchat', []))

    # Фильтруем содержимое
    filtered_contents = []
    for content in contents:
        obj = None
        quizzes = Quiz.objects.in_bulk(objects_by_type.get('quiz', []))

        if content.content_type.model == 'video':
            obj = videos.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'funfact':
            obj = funfacts.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'challenge':
            obj = challenges.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'chitchat':
            obj = chitchats.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'quiz':
            obj = quizzes.get(content.object_id)
            if obj and obj.title:
                content.quiz = obj
                content.quiz.total_points = sum(q.points for q in obj.questions.all())
                filtered_contents.append(content)

    return render(request, 'videos/reach_girl_page.html', {'contents': filtered_contents})


def money_talks_page(request):
    content_types = ContentType.objects.filter(
        model__in=['video', 'funfact', 'challenge', 'chitchat', 'quiz']
    )

    # Получаем все содержимое с предварительной выборкой
    contents = Content.objects.filter(
        content_type__in=content_types,
        page='its_time'
    ).select_related('content_type').order_by('id')

    # Создаем словарь для группировки объектов по типам
    from collections import defaultdict
    objects_by_type = defaultdict(list)

    for content in contents:
        objects_by_type[content.content_type.model].append(content.object_id)

    # Получаем все объекты одним запросом для каждого типа
    videos = Video.objects.in_bulk(objects_by_type.get('video', []))
    funfacts = FunFact.objects.in_bulk(objects_by_type.get('funfact', []))
    challenges = Challenge.objects.in_bulk(objects_by_type.get('challenge', []))
    chitchats = ChitChat.objects.in_bulk(objects_by_type.get('chitchat', []))

    # Фильтруем содержимое
    filtered_contents = []
    for content in contents:
        obj = None
        quizzes = Quiz.objects.in_bulk(objects_by_type.get('quiz', []))

        if content.content_type.model == 'video':
            obj = videos.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'funfact':
            obj = funfacts.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'challenge':
            obj = challenges.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'chitchat':
            obj = chitchats.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'quiz':
            obj = quizzes.get(content.object_id)
            if obj and obj.title:
                content.quiz = obj
                content.quiz.total_points = sum(q.points for q in obj.questions.all())
                filtered_contents.append(content)

    return render(request, 'videos/talk_money.html', {'contents': filtered_contents})


def you_do_you_page(request):
    # Получаем все ContentType одним запросом
    content_types = ContentType.objects.filter(
        model__in=['video', 'funfact', 'challenge', 'chitchat', 'quiz']
    )

    # Получаем все содержимое с предварительной выборкой
    contents = Content.objects.filter(
        content_type__in=content_types,
        page='you_do_you'
    ).select_related('content_type').order_by('id')

    # Создаем словарь для группировки объектов по типам
    from collections import defaultdict
    objects_by_type = defaultdict(list)

    for content in contents:
        objects_by_type[content.content_type.model].append(content.object_id)

    # Получаем все объекты одним запросом для каждого типа
    videos = Video.objects.in_bulk(objects_by_type.get('video', []))
    funfacts = FunFact.objects.in_bulk(objects_by_type.get('funfact', []))
    challenges = Challenge.objects.in_bulk(objects_by_type.get('challenge', []))
    chitchats = ChitChat.objects.in_bulk(objects_by_type.get('chitchat', []))

    # Фильтруем содержимое
    filtered_contents = []
    for content in contents:
        obj = None
        quizzes = Quiz.objects.in_bulk(objects_by_type.get('quiz', []))

        if content.content_type.model == 'video':
            obj = videos.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'funfact':
            obj = funfacts.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'challenge':
            obj = challenges.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'chitchat':
            obj = chitchats.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'quiz':
            obj = quizzes.get(content.object_id)
            if obj and obj.title:
                content.quiz = obj
                content.quiz.total_points = sum(q.points for q in obj.questions.all())
                filtered_contents.append(content)

    return render(request, 'videos/you_do_you.html', {'contents': filtered_contents})


def levers_page(request):
    # Получаем все ContentType одним запросом
    content_types = ContentType.objects.filter(
        model__in=['video', 'funfact', 'challenge', 'chitchat', 'quiz']
    )

    # Получаем все содержимое с предварительной выборкой
    contents = Content.objects.filter(
        content_type__in=content_types,
        page='levers'
    ).select_related('content_type').order_by('id')

    # Создаем словарь для группировки объектов по типам
    from collections import defaultdict
    objects_by_type = defaultdict(list)

    for content in contents:
        objects_by_type[content.content_type.model].append(content.object_id)

    # Получаем все объекты одним запросом для каждого типа
    videos = Video.objects.in_bulk(objects_by_type.get('video', []))
    funfacts = FunFact.objects.in_bulk(objects_by_type.get('funfact', []))
    challenges = Challenge.objects.in_bulk(objects_by_type.get('challenge', []))
    chitchats = ChitChat.objects.in_bulk(objects_by_type.get('chitchat', []))

    # Фильтруем содержимое
    filtered_contents = []
    for content in contents:
        obj = None
        quizzes = Quiz.objects.in_bulk(objects_by_type.get('quiz', []))

        if content.content_type.model == 'video':
            obj = videos.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'funfact':
            obj = funfacts.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'challenge':
            obj = challenges.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'chitchat':
            obj = chitchats.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'quiz':
            obj = quizzes.get(content.object_id)
            if obj and obj.title:
                content.quiz = obj
                content.quiz.total_points = sum(q.points for q in obj.questions.all())
                filtered_contents.append(content)

    return render(request, 'videos/levers.html', {'contents': filtered_contents})


def portfolio_page(request):
    # Получаем все ContentType одним запросом
    content_types = ContentType.objects.filter(
        model__in=['video', 'funfact', 'challenge', 'chitchat', 'quiz']
    )

    # Получаем все содержимое с предварительной выборкой
    contents = Content.objects.filter(
        content_type__in=content_types,
        page='portfolio'
    ).select_related('content_type').order_by('id')

    # Создаем словарь для группировки объектов по типам
    from collections import defaultdict
    objects_by_type = defaultdict(list)

    for content in contents:
        objects_by_type[content.content_type.model].append(content.object_id)

    # Получаем все объекты одним запросом для каждого типа
    videos = Video.objects.in_bulk(objects_by_type.get('video', []))
    funfacts = FunFact.objects.in_bulk(objects_by_type.get('funfact', []))
    challenges = Challenge.objects.in_bulk(objects_by_type.get('challenge', []))
    chitchats = ChitChat.objects.in_bulk(objects_by_type.get('chitchat', []))

    # Фильтруем содержимое
    filtered_contents = []
    for content in contents:
        obj = None
        quizzes = Quiz.objects.in_bulk(objects_by_type.get('quiz', []))

        if content.content_type.model == 'video':
            obj = videos.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'funfact':
            obj = funfacts.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'challenge':
            obj = challenges.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'chitchat':
            obj = chitchats.get(content.object_id)
            if obj and obj.title:
                filtered_contents.append(content)
        elif content.content_type.model == 'quiz':
            obj = quizzes.get(content.object_id)
            if obj and obj.title:
                content.quiz = obj
                content.quiz.total_points = sum(q.points for q in obj.questions.all())
                filtered_contents.append(content)

    return render(request, 'videos/portfolio.html', {'contents': filtered_contents})


def get_objects(request):
    content_type_id = request.GET.get('content_type')
    content_type = ContentType.objects.get(id=content_type_id)

    if content_type.model == 'funfact':
        objects = FunFact.objects.all()
    elif content_type.model == 'video':
        objects = Video.objects.all()
    else:
        objects = []

    data = [{'id': obj.id, 'title': str(obj)} for obj in objects]
    return JsonResponse(data, safe=False)


def video_detail(request, video_id):
    video = get_object_or_404(Video, id=video_id)

    points_added = 0
    if request.user.is_authenticated:
        # Получаем или создаём связанный объект Content
        content_type = ContentType.objects.get_for_model(Video)
        content, created = Content.objects.get_or_create(
            content_type=content_type,
            object_id=video.id,
            defaults={'title': video.title}  # обязательные поля Content
        )

        # Если видео ещё не просмотрено
        if not request.user.completed_content.filter(pk=content.pk).exists():
            points_added = video.points  # предполагаем, что у модели Video есть поле points
            request.user.points_count += points_added
            request.user.completed_content.add(content)
            request.user.save()

    return render(request, 'videos/video.html', {
        'video': video,
        'points_added': points_added
    })


def fun_fact_detail(request, fun_fact_id):
    fun_fact = get_object_or_404(FunFact, id=fun_fact_id)

    # Инициализируем переменные для шаблона
    points_added = 0
    added_to_completed = False

    if request.user.is_authenticated:
        # Получаем или создаем связанный объект Content
        content_type = ContentType.objects.get_for_model(FunFact)
        content, created = Content.objects.get_or_create(
            content_type=content_type,
            object_id=fun_fact.id,
            defaults={
                'title': fun_fact.title,
                # добавьте другие обязательные поля модели Content
            }
        )

        # Проверяем, не просмотрен ли уже этот факт
        if not request.user.completed_content.filter(pk=content.pk).exists():
            # Начисляем баллы (предполагаем, что у FunFact есть поле points)
            points_added = fun_fact.points
            request.user.points_count += points_added

            # Добавляем в completed_content
            request.user.completed_content.add(content)
            request.user.save()

            added_to_completed = True

    return render(request, 'videos/fun_fact.html', {
        'fun_fact': fun_fact,
        'points_added': points_added,
        'added_to_completed': added_to_completed
    })


def chitchat_detail(request, pk):
    chitchat = get_object_or_404(ChitChat, pk=pk)
    options = list(chitchat.options.all())  # Преобразуем в список для модификации

    try:
        user_choice = ChitChatUserChoice.objects.get(user=request.user, chit_chat=chitchat)
        answers_dict = {
            answer.option_pair_id: answer.answer
            for answer in user_choice.answers.all()
        }
    except ChitChatUserChoice.DoesNotExist:
        answers_dict = {}

    # Добавляем user_answer в каждый option
    for opt in options:
        opt.user_answer = answers_dict.get(opt.id, '')

    context = {
        'chit_chat': chitchat,
        'option_pairs': options,
    }
    return render(request, 'videos/chit_chat.html', context)


def chit_chat_view(request, chit_chat_id):
    chit_chat = get_object_or_404(ChitChat, pk=chit_chat_id)
    user_choices = {}

    if request.user.is_authenticated:
        try:
            user_choice = ChitChatUserChoice.objects.get(
                user=request.user,
                chit_chat=chit_chat
            )
            user_choices = user_choice.choices
        except ChitChatUserChoice.DoesNotExist:
            pass

    return render(request, 'your_template.html', {
        'chit_chat': chit_chat,
        'user_choices': user_choices,
        # остальные переменные
    })


@login_required
def choice_view(request, chit_chat_id):
    chit_chat = get_object_or_404(ChitChat, id=chit_chat_id)

    # Получаем все пары вариантов для этого ChitChat
    option_pairs = chit_chat.options.all()  # Предполагается, что связь называется 'options'

    # Получаем или создаем запись пользователя
    user_choice, created = ChitChatUserChoice.objects.get_or_create(
        user=request.user,
        chit_chat=chit_chat,
        defaults={'choices': {}}
    )

    if request.method == 'POST':
        # Собираем все выборы из формы
        new_choices = {}
        for pair in option_pairs:
            field_name = f'pair-{pair.id}'
            selected = request.POST.get(field_name)
            if selected:
                new_choices[str(pair.id)] = selected

        # Обновляем записи
        user_choice.choices = new_choices
        user_choice.save()
        return redirect('success_page')

    # Подготовка данных для отображения сохраненных выборов
    user_choices = {}
    if request.user.is_authenticated:
        choices = ChitChatUserChoice.objects.filter(user=request.user, chit_chat=chit_chat)
        for choice in choices:
            user_choices[f'pair-{choice.pair_number}'] = choice.selected_option

    return render(request, 'your_template.html', {
        'chit_chat': chit_chat,
        'option_pairs': option_pairs,
        'user_choices': user_choices
    })


def success_page(request):
    return render(request, 'videos/success_page.html')


def content_list(request):
    content = Content.objects.all()
    return render(request, 'videos/content.html', {'content': content})


@csrf_exempt
def chitchat_submit(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})

    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=403)

    chitchat = get_object_or_404(ChitChat, pk=pk)

    # Получаем связанный объект Content
    content_type = ContentType.objects.get_for_model(ChitChat)
    content, created = Content.objects.get_or_create(
        content_type=content_type,
        object_id=chitchat.id,
        defaults={'title': chitchat.title}  # или другие поля Content
    )

    # Проверяем, не проходил ли пользователь этот чит-чат ранее
    is_first_attempt = not request.user.completed_content.filter(pk=content.pk).exists()

    # Получаем или создаём запись выбора пользователя
    user_choice, _ = ChitChatUserChoice.objects.get_or_create(
        chit_chat=chitchat,
        user=request.user
    )
    user_choice.answers.all().delete()  # Удалим старые ответы

    # Сохраняем новые ответы
    data = request.POST
    for key, value in data.items():
        if key.startswith('pair-'):
            try:
                option_pair_id = int(key.split('-')[1])
                option_pair = ChitChatOption.objects.get(id=option_pair_id)
                ChitChatAnswer.objects.create(
                    user_choice=user_choice,
                    option_pair=option_pair,
                    answer=value
                )
            except (ValueError, ChitChatOption.DoesNotExist):
                continue

    # Если это первое прохождение - начисляем баллы и добавляем в completed_content
    if is_first_attempt:
        request.user.points_count += chitchat.points  # предполагаем, что у ChitChat есть поле points
        request.user.completed_content.add(content)
        request.user.save()
        return JsonResponse({
            'success': True,
            'points_added': chitchat.points,
            'message': f'Chit chat done! You get {chitchat.points} points'
        })

    return JsonResponse({
        'success': True,
        'points_added': 0,
        'message': 'Answer saved!'
    })


def challenge_detail(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)

    # Проверяем, есть ли у пользователя ответы на этот челлендж
    user_choices = ChallengeUserChoice.objects.filter(user=request.user, challenge=challenge)
    has_answers = user_choices.exists()

    return render(request, 'videos/challenge_welcome.html', {
        'challenge': challenge,
        'has_answers': has_answers,  # Передаем информацию о наличии ответов
    })


def challenge_detail_content(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    for element in challenge.elements.all():
        if element.element == "radio":
            element.options = [opt.strip() for opt in element.value.split(",")]
    return render(request, "videos/content.html", {"challenge": challenge})


def parse_radio_values(value_string):
    options = []
    for raw in value_string.split(","):
        raw = raw.strip()
        match = re.match(r"^(.*?)\s*(\(#([^)]*)\))?$", raw)  # Захватываем любые символы между "(#" и ")"
        if match:
            label = match.group(1).strip()
            color_match = match.group(3)  # Извлекаем цвет из группы 3, если он есть
            color = f"#{color_match}" if color_match else None  # Добавляем "#" перед цветом, если он найден
            options.append({"label": label, "color": color})
    return options


def challenge_add_content(request, pk):
    challenge = get_object_or_404(Challenge, pk=pk)

    elements_with_options = []
    for element in challenge.elements.filter(show_after_confirm=False):
        if element.element == "radio":
            options = parse_radio_values(element.value)
            elements_with_options.append({
                "element": element,
                "options": options,
            })
        else:
            elements_with_options.append({
                "element": element,
                "options": None,
            })

    return render(request, 'videos/challenge_add_content.html', {
        'challenge': challenge,
        'elements_with_options': elements_with_options,
    })


def normalize_label(label):
    return re.sub(r"\s+", "", label).lower()

def challenge_view_content(request, pk):
    challenge = get_object_or_404(Challenge, pk=pk)
    user_choices = ChallengeUserChoice.objects.filter(
        user=request.user,
        challenge=challenge
    ).prefetch_related('attempts__answers')

    logger.info("User choices: %s", user_choices)  # Логирование user_choices

    display_settings = getattr(challenge, 'display_settings', None)
    display_type = display_settings.display_type if display_settings else 'text'

    elements_to_show_after_confirm = challenge.elements.filter(show_after_confirm=True)

    # Добавляем опции для радиокнопок
    for element in elements_to_show_after_confirm:
        if element.element == "radio":
            element.options = element.get_options()
        else:
            element.options = None

    is_submit_active = user_choices.filter(attempts__is_done=True).count() >= challenge.min_answers_required

    for choice in user_choices:
        for attempt in choice.attempts.all():
            block_color = None

            for answer in attempt.answers.all():
                element = answer.element

                if element and element.value:
                    value = answer.answer
                    options = parse_radio_values(element.value)
                    matched = next(
                        (opt for opt in options if normalize_label(opt['label']) == normalize_label(value)),
                        None
                    )

                    if matched and matched['color']:
                        block_color = matched['color']
                        break

            attempt.block_color = block_color

            if display_type == 'text':
                attempt.text_display = []
                if display_settings and hasattr(display_settings, 'text_fields'):
                    for field in display_settings.text_fields.all():
                        answer = attempt.answers.filter(element=field.element).first()
                        value = answer.answer if answer else "—"
                        color = None

                        if field.element.field_type == 'radio':
                            options = parse_radio_values(field.element.value)
                            matched = next(
                                (opt for opt in options if normalize_label(opt['label']) == normalize_label(value)),
                                None
                            )
                            color = matched['color'] if matched else None

                        attempt.text_display.append({
                            'label': field.element.name,
                            'value': value,
                            'color': color
                        })

            elif display_type == 'table':
                attempt.table_cells = []
                for column in display_settings.table_columns.all():
                    value = "—"
                    color = None
                    if column.element:
                        answer = attempt.answers.filter(element=column.element).first()
                        value = answer.answer if answer else "—"

                        if column.element.field_type == 'radio':
                            options = parse_radio_values(column.element.value)
                            matched = next(
                                (opt for opt in options if normalize_label(opt['label']) == normalize_label(value)),
                                None
                            )
                            color = matched['color'] if matched else None

                    attempt.table_cells.append({
                        'value': value,
                        'color': color
                    })

        if display_type == 'table':
            choice.attempts_filtered = [
                a for a in choice.attempts.all()
                if not a.is_secondary and hasattr(a, 'table_cells') and any(
                    cell['value'].strip() for cell in a.table_cells)
            ]
        else:
            choice.attempts_filtered = choice.attempts.all()

    logger.info("Passing to template: %s", {
        'challenge': challenge,
        'user_choices': user_choices,
        'display_type': display_type,
        'display_settings': display_settings,
    })

    return render(request, 'videos/challenge_view_content.html', {
        'challenge': challenge,
        'user_choices': user_choices,
        'display_type': display_type,
        'display_settings': display_settings,
        'min_answers_required': challenge.min_answers_required,
        'is_submit_active': is_submit_active,
        'elements_to_show_after_confirm': elements_to_show_after_confirm,
    })


@require_POST
def mark_done(request, attempt_id):
    attempt = get_object_or_404(ChallengeUserAttempt, pk=attempt_id)
    attempt.is_done = True
    attempt.save()
    return JsonResponse({'status': 'done'})

@require_POST
def mark_undone(request, attempt_id):
    attempt = get_object_or_404(ChallengeUserAttempt, pk=attempt_id)
    attempt.is_done = False
    attempt.save()
    return JsonResponse({'status': 'undone'})


@require_POST
def delete_attempt(request, attempt_id):
    attempt = get_object_or_404(ChallengeUserAttempt, pk=attempt_id)
    attempt.delete()
    return JsonResponse({'status': 'deleted'})


@login_required
def submit_challenge(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)

    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        try:
            user_choice, _ = ChallengeUserChoice.objects.get_or_create(
                user=request.user,
                challenge=challenge
            )

            attempt = ChallengeUserAttempt.objects.create(
                choice=user_choice,
                is_secondary=True
            )

            for element in challenge.elements.all():
                field_name = f"field_{element.id}"
                answer_value = request.POST.get(field_name)

                if answer_value is not None:
                    ChallengeUserAnswer.objects.create(
                        attempt=attempt,
                        element=element,
                        answer=answer_value
                    )

            if is_ajax:
                return JsonResponse({'success': True, 'message': 'Answer saved successfully!'})
            else:
                messages.success(request, "Answer saved successfully!")
                return redirect('challenge_view_content', pk=challenge.id)

        except Exception as e:
            print("Ошибка при сохранении:", e)

            if is_ajax:
                return JsonResponse({'success': False, 'message': f"Ошибка при сохранении: {str(e)}"})
            else:
                messages.error(request, f"Ошибка при сохранении: {e}")
                return redirect('challenge_view_content', pk=challenge.id)

    # GET-запрос — отдаем форму
    elements_with_options = []
    for element in challenge.elements.filter(show_after_confirm=False):
        if element.element == "radio":
            options = parse_radio_values(element.value)
            elements_with_options.append({
                "element": element,
                "options": options,
            })
        else:
            elements_with_options.append({
                "element": element,
                "options": None,
            })

    return render(request, 'videos/challenge_view_content.html', {
        'challenge': challenge,
        'elements_with_options': elements_with_options,
    })

@login_required
def submit_challenge_in_add(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)

    points_added = 0

    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        try:
            # Получаем или создаем выбор пользователя для данного челленджа
            user_choice, _ = ChallengeUserChoice.objects.get_or_create(
                user=request.user,
                challenge=challenge
            )

            # Создаём новую попытку
            attempt = ChallengeUserAttempt.objects.create(
                choice=user_choice
            )

            # Сохраняем ответы на элементы челленджа
            for element in challenge.elements.all():
                field_name = f"field_{element.id}"
                answer_value = request.POST.get(field_name)

                if answer_value is not None:
                    ChallengeUserAnswer.objects.create(
                        attempt=attempt,
                        element=element,
                        answer=answer_value
                    )

            # Теперь считаем, сколько попыток создано (не важно, завершены или нет)
            user_choice = ChallengeUserChoice.objects.get(user=request.user, challenge=challenge)
            created_attempts_count = user_choice.attempts.count()  # Считаем все попытки

            # Проверяем, равно ли количество попыток минимальному количеству
            if created_attempts_count == challenge.min_answers_required:
                # Проверяем, были ли уже начислены баллы для этого челленджа
                if not request.user.completed_content.filter(id=challenge.id).exists():
                    # Начисляем баллы, если условие min_answers_required выполнено и еще не начислены
                    points_added = challenge.points
                    request.user.points_count += points_added  # Добавляем баллы к счету пользователя
                    request.user.save()  # Сохраняем изменения в пользователе

                    # Создаём или извлекаем объект Content для челленджа
                    content_type = ContentType.objects.get_for_model(Challenge)
                    content, created = Content.objects.get_or_create(
                        content_type=content_type,
                        object_id=challenge.id,
                        defaults={'title': challenge.title}
                    )

                    # Добавляем в completed_content
                    request.user.completed_content.add(content)

            if is_ajax:
                return JsonResponse({'success': True, 'message': 'Answer saved successfully!', 'points_added': points_added})
            else:
                if points_added > 0:
                    messages.success(request, f"Answer saved successfully! You earned {points_added} points.")
                return redirect('challenge_view_content', pk=challenge.id)

        except Exception as e:
            print("Ошибка при сохранении:", e)

            if is_ajax:
                return JsonResponse({'success': False, 'message': f"Ошибка при сохранении: {str(e)}"})
            else:
                messages.error(request, f"Ошибка при сохранении: {e}")
                return redirect('challenge_view_content', pk=challenge.id)


@login_required
def edit_challenge_attempt(request, attempt_id):
    attempt = get_object_or_404(ChallengeUserAttempt, pk=attempt_id, choice__user=request.user)
    challenge = attempt.choice.challenge

    answers = {
        ans.element.id: ans.answer
        for ans in attempt.answers.all()
    }

    elements_with_options = []
    for element in challenge.elements.filter(show_after_confirm=False):
        options = parse_radio_values(element.value) if element.element == "radio" else None
        elements_with_options.append({
            "element": element,
            "options": options,
            "value": answers.get(element.id)
        })

    return render(request, 'videos/challenge_add_content.html', {
        'challenge': challenge,
        'elements_with_options': elements_with_options,
        'editing': True,
        'attempt_id': attempt.id,
    })


@login_required
@require_POST
def update_challenge_attempt(request, attempt_id):
    attempt = get_object_or_404(ChallengeUserAttempt, pk=attempt_id, choice__user=request.user)
    challenge = attempt.choice.challenge

    try:
        for element in challenge.elements.all():
            field_name = f"field_{element.id}"
            answer_value = request.POST.get(field_name)
            if answer_value is not None:
                ChallengeUserAnswer.objects.update_or_create(
                    attempt=attempt,
                    element=element,
                    defaults={'answer': answer_value}
                )

        return JsonResponse({'success': True, 'message': 'Changes saved!'})

    except Exception as e:
        print("Error while updating:", e)
        return JsonResponse({'success': False, 'message': f'Error: {e}'}, status=500)


@login_required
def save_attempts_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            for item in data.get('attempts', []):
                attempt_id = item.get('id')
                is_done = item.get('is_done')
                cancel_edit_delete = item.get('cancel_edit_delete', False)

                old_attempt = ChallengeUserAttempt.objects.get(id=attempt_id)

                if cancel_edit_delete:
                    # Создаем новую попытку с теми же параметрами
                    new_name = f"Ответ от {timezone.now().strftime('%d.%m.%Y %H:%M')}"
                    new_attempt = ChallengeUserAttempt.objects.create(
                        user=old_attempt.user,
                        challenge=old_attempt.challenge,
                        is_done=is_done,
                        name=new_name
                    )

                    # Копируем все ответы
                    for answer in old_attempt.answers.all():
                        answer.pk = None  # создаёт копию объекта
                        answer.attempt = new_attempt
                        answer.save()
                else:
                    # Просто обновляем текущую попытку
                    old_attempt.is_done = is_done
                    old_attempt.save()

            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})



def quiz_detail(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)
    return render(request, 'videos/quiz.html', {'quiz': quiz})


def quiz_detail_welcome(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)
    total_points = sum(q.points for q in quiz.questions.all())
    return render(request, 'videos/quiz_welcome.html', {
        'quiz': quiz,
        'total_points': total_points,
    })


def quiz_start(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    return render(request, 'quiz/quiz.html', {'quiz': quiz})


def get_question(request, quiz_id, question_num):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    questions = quiz.questions.all().order_by('id')

    if question_num <= 0 or question_num > questions.count():
        return JsonResponse({'error': 'Invalid question number'}, status=400)

    question = questions[question_num - 1]
    data = {
        'question': question.text,
        'image': question.image.url if question.image else None,
        'question_type': question.question_type,
        'choices': question.choice_list if question.question_type in ['multiple', 'single'] else [],
        'current_question': question_num,
        'total_questions': questions.count(),
    }
    return JsonResponse(data)


def quiz_results(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)
    try:
        user_choice = QuizUserChoice.objects.get(user=request.user, quiz=quiz)
        answers = user_choice.answers.select_related('question')

        correct_answers = answers.filter(is_correct=True)
        correct_count = correct_answers.count()
        earned_points = sum(answer.question.points for answer in correct_answers)
        max_possible_points = quiz.total_points()

        points_awarded_already = user_choice.points_awarded  # <- сохраняем в переменную до изменения!

        if not user_choice.points_awarded:
            request.user.points_count += earned_points
            content_type = ContentType.objects.get_for_model(Quiz)
            try:
                content = Content.objects.get(content_type=content_type, object_id=quiz.id)
                request.user.completed_content.add(content)
            except Content.DoesNotExist:
                # Обработка случая, если Content не найден
                pass
            request.user.save()
            user_choice.points_awarded = True
            user_choice.save()

        incorrect_answers = answers.filter(is_correct=False)
        incorrect_count = incorrect_answers.count()

        request.session['incorrect_question_ids'] = [ans.question.id for ans in incorrect_answers]
        request.session['quiz_id_for_review'] = pk

        return render(request, 'videos/quiz_results.html', {
            'quiz': quiz,
            'correct_count': correct_count,
            'total_questions': quiz.questions_count(),
            'earned_points': earned_points,
            'max_possible_points': max_possible_points,
            'incorrect_count': incorrect_count,
            'points_awarded_already': points_awarded_already,
            'added_to_completed': not points_awarded_already,
        })
    except QuizUserChoice.DoesNotExist:
        return redirect('quiz_detail', pk=pk)


def get_incorrect_question(request, quiz_id, index):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    question_ids = request.session.get('incorrect_question_ids', [])

    if not question_ids or index < 0 or index >= len(question_ids):
        return JsonResponse({'error': 'Invalid question'}, status=400)

    question = get_object_or_404(QuizQuestion, pk=question_ids[index])

    data = {
        'question': question.text,
        'image': question.image.url if question.image else None,
        'question_type': question.question_type,
        'choices': question.choice_list if question.question_type in ['multiple', 'single'] else [],
        'current_index': index,
        'total_incorrect': len(question_ids),
        'correct_answer': question.correct_answers  # Добавляем правильный ответ
    }
    return JsonResponse(data)


def start_incorrect_review(request):
    question_ids = request.session.get('incorrect_question_ids', [])
    if not question_ids:
        return redirect('quiz_results', pk=request.session.get('quiz_id_for_review'))

    # Перенаправляем на первый неправильный вопрос
    return redirect('quiz_question_review', question_id=question_ids[0], index=0)


def quiz_question_review(request, question_id, index):
    question = get_object_or_404(QuizQuestion, pk=question_id)
    question_ids = request.session.get('incorrect_question_ids', [])
    quiz_id = request.session.get('quiz_id_for_review')

    if not quiz_id or index < 0 or index >= len(question_ids):
        return redirect('quiz_results', pk=quiz_id)

    # Получаем ответ пользователя
    user_choice = QuizUserChoice.objects.get(user=request.user, quiz_id=quiz_id)
    user_answer = QuizAnswer.objects.get(
        quiz_user_choice=user_choice,
        question=question
    )

    # Подготавливаем данные для навигации
    prev_question_id = question_ids[index-1] if index > 0 else None
    next_question_id = question_ids[index+1] if index < len(question_ids)-1 else None

    return render(request, 'videos/quiz_review.html', {
        'question': question,
        'user_answer': user_answer.user_answer,
        'correct_answer': question.correct_answers,
        'current_index': index,
        'total_incorrect': len(question_ids),
        'quiz_id': quiz_id,
        'prev_question_id': prev_question_id,  # Добавляем ID предыдущего вопроса
        'next_question_id': next_question_id   # Добавляем ID следующего вопроса
    })


def submit_answer(request):
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            data = json.loads(request.body)
            quiz_id = data.get('quiz_id')
            answers = data.get('answers')

            if not quiz_id or not answers:
                return JsonResponse({'error': 'Missing quiz_id or answers'}, status=400)

            quiz = get_object_or_404(Quiz, pk=quiz_id)
            questions = quiz.questions.all().order_by('id')

            # Создаем или получаем запись QuizUserChoice
            quiz_user_choice, created = QuizUserChoice.objects.get_or_create(
                user=request.user,
                quiz=quiz,
                defaults={'submitted_at': timezone.now()}
            )

            # Сохраняем все ответы
            for question_num, user_answer in answers.items():
                try:
                    question_num = int(question_num)
                    if question_num <= 0 or question_num > questions.count():
                        continue

                    question = questions[question_num - 1]

                    # Проверяем правильность ответа
                    is_correct = False
                    if question.question_type == 'input':
                        is_correct = user_answer.lower() == question.correct_answers.lower()
                    elif question.question_type == 'single':
                        is_correct = user_answer == question.correct_answers
                    elif question.question_type == 'multiple':
                        correct_answers = set(question.correct_answers.split(','))
                        user_answers = set(user_answer.split(','))
                        is_correct = correct_answers == user_answers

                    # Создаем или обновляем ответ
                    QuizAnswer.objects.update_or_create(
                        quiz_user_choice=quiz_user_choice,
                        question=question,
                        defaults={
                            'user_answer': user_answer,
                            'is_correct': is_correct
                        }
                    )

                except (ValueError, IndexError):
                    continue

            # Очищаем localStorage после успешной отправки
            return JsonResponse({
                'status': 'success',
                'redirect_url': reverse('quiz_results', kwargs={'pk': quiz_id})
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)