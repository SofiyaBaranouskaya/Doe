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
    QuizUserChoice, QuizAnswer, QuizQuestion, Invitation, Glossary, Favourites, UserReward, Rewards, Page
from django.contrib.auth import authenticate, login, get_backends, logout
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth import get_user_model
from collections import defaultdict
from django.core.mail import send_mail
from django.conf import settings
from utils.supabase_upload import upload_user_avatar
from utils.generate_avatar import generate_initial_avatar
import logging
from .tasks import process_uploaded_file


User = get_user_model()
logger = logging.getLogger(__name__)
def tester(request):
    return render(request, 'test.html')

def onboarding_view1(request):
    return render(request, 'users/onboarding1.html')

def onboarding_view2(request):
    return render(request, 'users/onboarding2.html')

def onboarding_view3(request):
    return render(request, 'users/onboarding3.html')

def profile_end(request):
    return render(request, 'users/profile_end.html')

def events_page(request):
    return render(request, 'videos/events_page.html')

def simulator_page(request):
    return render(request, 'videos/simulator_page.html')

def glossary_page(request):
    items = Glossary.objects.all().order_by("order")
    return render(request, "videos/glossary_page.html", {"items": items})

def saved_page(request):
    return render(request, 'videos/saved_page.html')

def hot_takes_page(request):
    return render(request, 'videos/hot_takes_page.html')


def favourites_page(request):
    if not request.user.is_authenticated:
        return render(request, 'videos/favourites_page.html', {'contents': []})

    # Все лайки пользователя
    favourites = Favourites.objects.filter(user=request.user).select_related('content_type')

    if not favourites.exists():
        return render(request, 'videos/favourites_page.html', {'contents': []})

    # Группируем id по типу контента
    objects_by_type = defaultdict(list)
    ct_by_model = {}  # чтобы потом быстро получить ContentType

    for fav in favourites:
        model_name = fav.content_type.model
        objects_by_type[model_name].append(fav.object_id)
        ct_by_model[model_name] = fav.content_type

    # Загружаем объекты одним запросом на тип
    videos    = Video.objects.in_bulk(objects_by_type.get('video', []))
    funfacts  = FunFact.objects.in_bulk(objects_by_type.get('funfact', []))
    challenges = Challenge.objects.in_bulk(objects_by_type.get('challenge', []))
    chitchats = ChitChat.objects.in_bulk(objects_by_type.get('chitchat', []))
    quizzes   = Quiz.objects.in_bulk(objects_by_type.get('quiz', []))

    filtered_contents = []

    for fav in favourites:
        model = fav.content_type.model
        obj = None

        if model == 'video':
            obj = videos.get(fav.object_id)
        elif model == 'funfact':
            obj = funfacts.get(fav.object_id)
        elif model == 'challenge':
            obj = challenges.get(fav.object_id)
        elif model == 'chitchat':
            obj = chitchats.get(fav.object_id)
        elif model == 'quiz':
            obj = quizzes.get(fav.object_id)

        if not obj or not getattr(obj, 'title', None):
            continue

        # Создаём объект, максимально похожий на то, что ожидает шаблон
        class FakeContent:
            pass

        content = FakeContent()

        content.content_type     = fav.content_type           # важно!
        content.object_id        = fav.object_id
        content.is_liked         = True                       # на странице избранного всегда True
        content.value            = obj                        # ← основной объект модели
        content.quiz             = None
        content.poster_base64    = getattr(obj, 'poster_base64', None) if model == 'video' else None

        # duration и points — как в основной логике
        content.duration = getattr(obj, 'duration', None)
        content.points   = getattr(obj, 'points', None)

        if model == 'quiz':
            total_points = sum(q.points for q in obj.questions.all())
            content.points = total_points
            content.quiz = obj
            content.quiz.total_points = total_points   # для шаблона {{ content.quiz.total_points }}

        # Для совместимости с условиями вида content.value.duration / content.value.points
        # (хотя теперь можно использовать content.duration и content.points напрямую)
        content.value = obj

        filtered_contents.append(content)

    context = {
        'contents': filtered_contents,
        # если в шаблоне используется page.title или другие поля — можно добавить заглушку
        'page': type('Page', (), {'title': 'Favourites', 'subtitle': 'Избранное'})(),
    }

    return render(request, 'videos/favourites_page.html', context)


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
    rewards = Rewards.objects.all()
    interests_list = []
    hobbies_list = []

    # Получаем Industry/Field
    if user.industry:
        interests_list = [i.strip() for i in user.industry.split(';;') if i.strip()]

    # Получаем Who Are You Today
    if user.you_today:
        hobbies_list = [h.strip() for h in user.you_today.split(';;') if h.strip()]

    completed_count = user.completed_content.count()

    # Форматируем дату регистрации
    from django.utils import timezone
    import calendar

    # Получаем месяц и год регистрации
    month_number = user.date_joined.month
    year = user.date_joined.year

    # Преобразуем номер месяца в название сезона
    if 3 <= month_number <= 5:
        season = "Spring"
    elif 6 <= month_number <= 8:
        season = "Summer"
    elif 9 <= month_number <= 11:
        season = "Fall"
    else:  # 12, 1, 2
        season = "Winter"

    formatted_date = f"Doe Member since {season} {year}"

    return render(request, 'videos/user_profile.html', {
        'user': user,
        'interests_list': interests_list,
        'hobbies_list': hobbies_list,
        'completed_count': completed_count,
        'rewards': rewards,
        'user_profile_picture_base64': user.get_profile_picture_base64(),
        'member_since': formatted_date,  # Добавляем в контекст
    })

def user_profile_change(request):
    user = request.user
    # rewards = Rewards.objects.all()
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
        # 'rewards': rewards,
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
@require_POST
def send_invite(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    data = json.loads(request.body)
    email = data.get('email')

    sender_email = request.user.email
    if not sender_email:
        return JsonResponse({'error': 'User email not found'}, status=400)

    # не приглашали ли уже
    if Invitation.objects.filter(
        inviter=request.user,
        invitee_email=email
    ).exists():
        return JsonResponse(
            {'message': 'Invitation already sent'},
            status=200
        )

    try:
        # СОЗДАЁМ ЗАПИСЬ В БД
        invitation = Invitation.objects.create(
            inviter=request.user,
            invitee_email=email,
        )

        base_url = request.build_absolute_uri('/')

        # ОТПРАВЛЯЕМ ПИСЬМО
        send_mail(
            subject="You're invited!",
            message=(
                f"{request.user.first_name} invited you to join Doe!\n\n"
                f"Join us here: {base_url}"
            ),
            from_email=sender_email,
            recipient_list=[email],
            fail_silently=False,
        )

        return JsonResponse({'message': 'Invitation sent successfully!'})

    except Exception as e:
        print(e)
        return JsonResponse({'error': 'Failed to send email.'}, status=500)



@login_required
def redeem_reward(request):
    if request.method == 'POST':
        reward_id = request.POST.get('selected_reward')
        if not reward_id:
            return JsonResponse({
                'success': False,
                'error': 'Please select a reward'
            })

        reward = get_object_or_404(Rewards, id=reward_id)
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
            user = form.save(commit=False)  # Не сохраняем сразу
            user.email = user.email.lower()  # Приводим email к lowercase
            user.save()  # Теперь сохраняем

            # Ищем приглашение (используем iexact для надёжности)
            invitation = Invitation.objects.filter(
                invitee_email__iexact=user.email,
                accepted=False
            ).first()

            if invitation:
                invitation.accepted = True
                invitation.save()

                user.points_count += 100
                inviter = User.objects.filter(email__iexact=invitation.inviter.email).first()
                if inviter:
                    inviter.points_count += 150
                    inviter.save()
                user.save()

                send_mail(...)  # Без изменений

            # Логиним пользователя
            backend = get_backends()[0]
            user.backend = f"{backend.__module__}.{backend.__class__.__name__}"
            login(request, user)
            return redirect('signup_complete')
    else:
        form = RegistrationForm()

    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('username', '').strip()  # Удаляем пробелы
        password = request.POST.get('password')

        # Если это email — приводим к lowercase
        if '@' in identifier:
            identifier = identifier.lower()

        user = User.objects.filter(
            Q(email__iexact=identifier) |  # iexact для регистронезависимости
            Q(phone_number=identifier)     # Телефон без изменений
        ).first()

        if user:
            user = authenticate(request, username=user.username, password=password)
            if user:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, 'Incorrect password.')
        else:
            messages.error(request, 'User with this email or telephone is not found.')

    return render(request, 'users/login.html')

def profile_view(request):
    schools = Schools.objects.all()
    return render(request, 'users/profile.html', {'schools': schools})


@login_required
def about_me_view(request):
    user = request.user

    # Проверяем, есть ли параметр next в URL (режим редактирования)
    edit_mode = 'next' in request.GET
    next_url = request.GET.get('next')

    if request.method == 'POST':
        # Для POST тоже проверяем
        edit_mode = 'next' in request.POST
        next_url = request.POST.get('next')

        # --- BASIC FIELDS ---
        first_name = request.POST.get('first_name')
        if first_name is not None:
            user.first_name = first_name.strip()

        last_name = request.POST.get('last_name')
        if last_name is not None:
            user.last_name = last_name.strip()

        curr_city = request.POST.get('curr_city')
        if curr_city is not None:
            user.curr_city = curr_city.strip()

        hometown = request.POST.get('hometown')
        if hometown is not None:
            user.hometown = hometown.strip()

        # --- DATE OF BIRTH ---
        dob = request.POST.get('dob')
        if dob:
            try:
                user.date_of_birth = datetime.strptime(dob, '%Y-%m-%d').date()
            except ValueError:
                pass

        # --- AVATAR ---
        if request.FILES.get('avatar'):
            user.profile_picture = request.FILES['avatar']

        user.save()

        # --- SCHOOLS ---
        UserSchool.objects.filter(user=user).delete()

        index = 0
        while f'schools[{index}][school_id]' in request.POST:

            school_id = request.POST.get(f'schools[{index}][school_id]')
            grad_year = request.POST.get(f'schools[{index}][grad_year]')
            other_name = request.POST.get(f'schools[{index}][other_name]', '').strip()

            if school_id and grad_year:

                if school_id == '0' and other_name:
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
                        pass

            index += 1

        # ВОЗВРАЩАЕМСЯ В ЗАВИСИМОСТИ ОТ РЕЖИМА
        if edit_mode and next_url:
            return redirect(next_url)
        else:
            return redirect('profile_your_next_move')

    # ---------- GET REQUEST ----------
    return render(request, 'users/profile/about_me.html', {
        'user': user,
        'schools': Schools.objects.all(),
        'user_schools': UserSchool.objects.filter(user=user),
        'edit_mode': edit_mode,
        'next': next_url if edit_mode else None,
    })


@login_required
def your_next_move_view(request):
    user = request.user

    # Проверяем, есть ли параметр next в URL (режим редактирования)
    edit_mode = 'next' in request.GET
    next_url = request.GET.get('next')

    if request.method == 'POST':
        # Для POST тоже проверяем
        edit_mode = 'next' in request.POST
        next_url = request.POST.get('next')

        raw = request.POST.get('chosenHobbies', '[]')
        try:
            values = json.loads(raw)
        except json.JSONDecodeError:
            values = []

        user.next_move = ';; '.join([v.strip() for v in values if v.strip()])
        user.save()

        # Возвращаемся в зависимости от режима
        if edit_mode and next_url:
            return redirect(next_url)
        else:
            return redirect('profile_current_vibe')

    current = []
    if user.next_move:
        current = [v.strip() for v in user.next_move.split(';;') if v.strip()]

    return render(request, 'users/profile/your_next_move.html', {
        'current_next_move': current,
        'edit_mode': edit_mode,
        'next': next_url if edit_mode else None,
    })


@login_required
def current_vibe_view(request):
    user = request.user

    # Проверяем, есть ли параметр next в URL (режим редактирования)
    edit_mode = 'next' in request.GET
    next_url = request.GET.get('next')

    if request.method == 'POST':
        # Для POST тоже проверяем
        edit_mode = 'next' in request.POST
        next_url = request.POST.get('next')

        user.current_vibe = request.POST.get('vibe', '').strip()
        user.save()

        # Возвращаемся в зависимости от режима
        if edit_mode and next_url:
            return redirect(next_url)
        else:
            return redirect('profile_industry_field')

    return render(request, 'users/profile/current_vibe.html', {
        'current_vibe': user.current_vibe,
        'edit_mode': edit_mode,
        'next': next_url if edit_mode else None,
    })


@login_required
def industry_field_view(request):
    user = request.user

    # Проверяем, есть ли параметр next в URL (режим редактирования)
    edit_mode = 'next' in request.GET
    next_url = request.GET.get('next')

    if request.method == 'POST':
        # Для POST тоже проверяем
        edit_mode = 'next' in request.POST
        next_url = request.POST.get('next')

        raw = request.POST.get('chosenHobbies', '[]')

        try:
            values = json.loads(raw)
        except:
            values = []

        # очистка и удаление дублей
        clean_values = []
        for v in values:
            v = v.strip()
            if v and v not in clean_values:
                clean_values.append(v)

        # сохранение через ;;
        user.industry = ';; '.join(clean_values)
        user.save()

        # Возвращаемся в зависимости от режима
        if edit_mode and next_url:
            return redirect(next_url)
        else:
            return redirect('profile_who_are_you_today')

    # восстановление
    current = []
    if user.industry:
        current = [
            v.strip()
            for v in user.industry.split(';;')
            if v.strip()
        ]

    return render(request, 'users/profile/industry_field.html', {
        'current_industries': current,
        'edit_mode': edit_mode,
        'next': next_url if edit_mode else None,
    })


@login_required
def who_are_you_today_view(request):
    user = request.user

    # Проверяем, есть ли параметр next в URL (режим редактирования)
    edit_mode = 'next' in request.GET
    next_url = request.GET.get('next')

    if request.method == 'POST':
        # Для POST тоже проверяем
        edit_mode = 'next' in request.POST
        next_url = request.POST.get('next')

        raw = request.POST.get('who_are_you_tags', '[]')
        try:
            values = json.loads(raw)
        except:
            values = []

        user.you_today = ';; '.join([v.strip() for v in values if v.strip()])
        user.save()

        # Возвращаемся в зависимости от режима
        if edit_mode and next_url:
            return redirect(next_url)
        else:
            return redirect('home')  # или другой финальный шаг

    current = []
    if user.you_today:
        current = [v.strip() for v in user.you_today.split(';;') if v.strip()]

    return render(request, 'users/profile/who_are_you_today.html', {
        'current_tags': current,
        'edit_mode': edit_mode,
        'next': next_url if edit_mode else None,
    })


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
        if 'avatar' in request.FILES:
            avatar_file = request.FILES['avatar']
            relative_path = upload_user_avatar(
                file=avatar_file,
                user_id=user.id,
                file_name=avatar_file.name,
                bucket_name='profile_pictures',
                content_type=avatar_file.content_type
            )
            if relative_path:
                user.profile_picture.name = relative_path  # <--- ВАЖНО!
                avatar_set = True

        # Генерация аватара, если пользователь ничего не загрузил
        if not avatar_set and not user.profile_picture:
            generated_buffer = generate_initial_avatar(user)
            if generated_buffer:
                relative_path = upload_user_avatar(
                    file=generated_buffer,
                    user_id=user.id,
                    file_name=f"avatar_{user.id}.png",
                    content_type='image/png',
                    bucket_name='profile_pictures'
                )
                if relative_path:
                    user.profile_picture.name = relative_path  # <--- И ЗДЕСЬ ТОЖЕ!
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
    pages = Page.objects.filter(is_active=True).order_by('order')
    return render(request, 'videos/home_page.html', {
        'pages': pages
    })

# def home_view(request):
#     progress_data = {
#         'money_talks': {'completed': 10, 'total': 100},
#         'reach_girl': {'completed': 30, 'total': 100},
#         'you_do_you': {'completed': 12, 'total': 100},
#         'levers': {'completed': 13, 'total': 100},
#         'portfolio': {'completed': 10, 'total': 100},
#     }
#     return render(request, 'videos/home_page.html')


def welcome_video(request):
    return render(request, 'videos/welcome_video.html')

# def render_page(request, page_name, template_name, extra_context=None):
#     content_types = ContentType.objects.filter(
#         model__in=['video', 'funfact', 'challenge', 'chitchat', 'quiz']
#     )
#
#     contents = Content.objects.filter(
#         content_type__in=content_types,
#         page=page_name
#     ).select_related('content_type').order_by('order')
#
#     from collections import defaultdict
#     objects_by_type = defaultdict(list)
#
#     for content in contents:
#         objects_by_type[content.content_type.model].append(content.object_id)
#
#     videos = Video.objects.in_bulk(objects_by_type.get('video', []))
#     funfacts = FunFact.objects.in_bulk(objects_by_type.get('funfact', []))
#     challenges = Challenge.objects.in_bulk(objects_by_type.get('challenge', []))
#     chitchats = ChitChat.objects.in_bulk(objects_by_type.get('chitchat', []))
#     quizzes = Quiz.objects.in_bulk(objects_by_type.get('quiz', []))
#
#     filtered_contents = []
#
#     for content in contents:
#         obj = None
#         model = content.content_type.model
#
#         if model == 'video':
#             obj = videos.get(content.object_id)
#         elif model == 'funfact':
#             obj = funfacts.get(content.object_id)
#         elif model == 'challenge':
#             obj = challenges.get(content.object_id)
#         elif model == 'chitchat':
#             obj = chitchats.get(content.object_id)
#         elif model == 'quiz':
#             obj = quizzes.get(content.object_id)
#             if obj:
#                 # считаем баллы квиза
#                 obj.total_points = sum(q.points for q in obj.questions.all())
#
#         if not obj or not getattr(obj, 'title', None):
#             continue
#
#         # единая точка доступа для шаблона
#         content.obj = obj
#
#         content.duration = getattr(obj, 'duration', None)
#
#         content.points = getattr(obj, 'points', None)
#         if model == 'quiz':
#             content.points = obj.total_points
#
#         filtered_contents.append(content)
#
#     # если пользователь не авторизован
#     if not request.user.is_authenticated:
#         for c in filtered_contents:
#             c.is_liked = False
#         context = {'contents': filtered_contents}
#         if extra_context:
#             context.update(extra_context)
#         return render(request, template_name, context)
#
#     # лайки пользователя
#     from collections import defaultdict
#     ct_to_ids = defaultdict(list)
#
#     for c in filtered_contents:
#         ct_to_ids[c.content_type_id].append(c.object_id)
#
#     likes = Favourites.objects.filter(
#         user=request.user,
#         content_type_id__in=ct_to_ids.keys(),
#         object_id__in=[oid for ids in ct_to_ids.values() for oid in ids]
#     )
#
#     liked_set = {(l.content_type_id, l.object_id) for l in likes}
#     print("1--------------------------", liked_set)
#
#     for c in filtered_contents:
#         c.is_liked = (c.content_type_id, c.object_id) in liked_set
#
#     print("2--------------------------", liked_set)
#
#     context = {'contents': filtered_contents}
#     if extra_context:
#         context.update(extra_context)
#
#     print("3--------------------------", liked_set)
#
#     return render(request, template_name, context)


def dynamic_page(request, slug):
    page = get_object_or_404(Page, slug=slug, is_active=True)

    content_types = ContentType.objects.filter(
        model__in=['video', 'funfact', 'challenge', 'chitchat', 'quiz']
    )

    contents = Content.objects.filter(
        content_type__in=content_types,
        page=page
    ).select_related('content_type').order_by('order')

    from collections import defaultdict
    objects_by_type = defaultdict(list)

    for content in contents:
        objects_by_type[content.content_type.model].append(content.object_id)

    videos = Video.objects.in_bulk(objects_by_type.get('video', []))
    funfacts = FunFact.objects.in_bulk(objects_by_type.get('funfact', []))
    challenges = Challenge.objects.in_bulk(objects_by_type.get('challenge', []))
    chitchats = ChitChat.objects.in_bulk(objects_by_type.get('chitchat', []))
    quizzes = Quiz.objects.in_bulk(objects_by_type.get('quiz', []))

    filtered_contents = []

    for content in contents:
        obj = None
        model = content.content_type.model

        if model == 'video':
            obj = videos.get(content.object_id)
        elif model == 'funfact':
            obj = funfacts.get(content.object_id)
        elif model == 'challenge':
            obj = challenges.get(content.object_id)
        elif model == 'chitchat':
            obj = chitchats.get(content.object_id)
        elif model == 'quiz':
            obj = quizzes.get(content.object_id)
            if obj and obj.title:
                content.quiz = obj
                content.quiz.total_points = sum(q.points for q in obj.questions.all())

        if not obj or not getattr(obj, 'title', None):
            continue

        content.obj = obj
        content.duration = getattr(obj, 'duration', None)
        content.points = getattr(obj, 'points', None)
        if model == 'quiz':
            content.points = obj.total_points

        filtered_contents.append(content)

    # 🔒 ВЫЧИСЛЯЕМ is_available ДЛЯ ВСЕХ (включая неавторизованных)
    if request.user.is_authenticated:
        # Предзагружаем completed_content для производительности
        completed_ids = set(request.user.completed_content.values_list('pk', flat=True))
        for c in filtered_contents:
            c.is_available = c.is_available_for_user(request.user, completed_ids=completed_ids)
    else:
        for c in filtered_contents:
            c.is_available = False  # Или True, если хотите показывать всё неавторизованным

    # если пользователь не авторизован
    if not request.user.is_authenticated:
        for c in filtered_contents:
            c.is_liked = False
        context = {
            'page': page,
            'contents': filtered_contents
        }
        return render(request, "videos/pages/page.html", context)

    # лайки пользователя
    ct_to_ids = defaultdict(list)
    for c in filtered_contents:
        ct_to_ids[c.content_type_id].append(c.object_id)

    likes = Favourites.objects.filter(
        user=request.user,
        content_type_id__in=ct_to_ids.keys(),
        object_id__in=[oid for ids in ct_to_ids.values() for oid in ids]
    )

    liked_set = {(l.content_type_id, l.object_id) for l in likes}

    for c in filtered_contents:
        c.is_liked = (c.content_type_id, c.object_id) in liked_set

    context = {
        'page': page,
        'contents': filtered_contents
    }

    return render(request, "videos/pages/page.html", context)


# def first_page(request):
#     return render_page(request, 'things_first', 'videos/pages/first_page.html')
#
# def second_page(request):
#     return render_page(request, 'levers', 'videos/pages/second_page.html')
#
# def third_page(request):
#     return render_page(request, 'power_portfolio', 'videos/pages/third_page.html')
#
# def forth_page(request):
#     return render_page(request, 'playbook', 'videos/pages/forth_page.html')
#
# def fifth_page(request):
#     return render_page(request, 'capital_cash', 'videos/pages/fifth_page.html')
#
# def sixth_page(request):
#     return render_page(request, 'money_sports', 'videos/pages/sixth_page.html')
#
# def seventh_page(request):
#     return render_page(request, 'new_ventures', 'videos/pages/seventh_page.html')
#
# def eighth_page(request):
#     return render_page(request, 'rel_money', 'videos/pages/eighth_page.html')


def toggle_like(request, model, object_id):
    try:
        ct = ContentType.objects.get(model=model)
    except ContentType.DoesNotExist:
        return JsonResponse({"error": "invalid_model"}, status=400)

    model_class = ct.model_class()
    if not model_class.objects.filter(pk=object_id).exists():
        return JsonResponse({"error": "object_not_found"}, status=404)

    fav, created = Favourites.objects.get_or_create(
        user=request.user,
        content_type=ct,
        object_id=object_id
    )

    if not created:
        fav.delete()
        return JsonResponse({"liked": False})

    return JsonResponse({"liked": True})

def signout(request):
    logout(request)
    return redirect('login')

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

    points_added = 0
    added_to_completed = False
    page_slug = None  # ← Добавляем переменную для slug страницы

    if request.user.is_authenticated:
        content_type = ContentType.objects.get_for_model(FunFact)

        content = Content.objects.filter(
            content_type=content_type,
            object_id=fun_fact.id
        ).first()

        if not content:
            content = Content.objects.create(
                content_type=content_type,
                object_id=fun_fact.id,
                title=fun_fact.title,
            )

        # 🔑 Получаем slug страницы из content.page
        if content and content.page:
            page_slug = content.page.slug

        # Проверяем, просмотрен ли уже
        if not request.user.completed_content.filter(pk=content.pk).exists():
            points_added = fun_fact.points
            request.user.points_count += points_added
            request.user.completed_content.add(content)
            request.user.save()
            added_to_completed = True

    return render(request, 'videos/fun_fact.html', {
        'fun_fact': fun_fact,
        'points_added': points_added,
        'added_to_completed': added_to_completed,
        'page_slug': page_slug,  # ← Передаём slug в шаблон
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

    try:
        chitchat = get_object_or_404(ChitChat, pk=pk)

        # Получаем или создаём Content, избегая ошибки MultipleObjectsReturned
        content_type = ContentType.objects.get_for_model(ChitChat)
        content = Content.objects.filter(content_type=content_type, object_id=chitchat.id).first()
        if not content:
            content = Content.objects.create(
                content_type=content_type,
                object_id=chitchat.id,
                title=chitchat.title
            )

        # Проверка на первое прохождение
        is_first_attempt = not request.user.completed_content.filter(pk=content.pk).exists()

        # Получаем или создаём выбор пользователя
        user_choice, _ = ChitChatUserChoice.objects.get_or_create(
            chit_chat=chitchat,
            user=request.user
        )
        user_choice.answers.all().delete()

        # Обработка ответов
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
                except (ValueError, ChitChatOption.DoesNotExist) as e:
                    logger.warning(f"Invalid option id or missing option: {key} - {e}")
                    continue

        # Начисление баллов
        if is_first_attempt:
            request.user.points_count += chitchat.points
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

    except Exception as e:
        logger.exception("Unexpected error during chitchat_submit")
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


def challenge_detail(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)

    # Получаем связанный контент для этого челленджа
    content_type = ContentType.objects.get_for_model(Challenge)
    contents = Content.objects.filter(
        object_id=challenge.id,
        content_type=content_type
    ).order_by('-id')  # Сортируем, чтобы взять последнюю запись

    # Берем последнюю запись или None, если нет записей
    content = contents.first() if contents.exists() else None
    content_page = content.page if content else None
    page_slug = content_page.slug if content_page else None

    # Проверяем, есть ли у пользователя ответы на этот челлендж
    user_choices = ChallengeUserChoice.objects.filter(user=request.user, challenge=challenge)
    has_answers = user_choices.exists()

    return render(request, 'videos/challenge_welcome.html', {
        'challenge': challenge,
        'has_answers': has_answers,  # Передаем информацию о наличии ответов
        'content_page': content_page,  # Добавляем страницу в контекст
        'page_slug': page_slug,
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

    # Получаем связанный контент для этого челленджа
    content_type = ContentType.objects.get_for_model(Challenge)
    contents = Content.objects.filter(
        object_id=challenge.pk,
        content_type=content_type
    ).order_by('-id')  # Сортируем, чтобы взять последнюю запись

    # Берем последнюю запись или None, если нет записей
    content = contents.first() if contents.exists() else None
    content_page = content.page if content else None
    page_slug = content_page.slug if content_page else None

    elements_with_options = []
    for element in challenge.elements.filter(show_after_confirm=False):
        if element.element in ["radio", "checkbox"]:
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
        'content_page': content_page,
        'page_slug': page_slug,
    })


def normalize_label(label):
    return re.sub(r"\s+", "", label).lower()


def challenge_view_content(request, pk):
    challenge = get_object_or_404(Challenge, pk=pk)

    # Получаем связанную страницу контента
    content_type = ContentType.objects.get_for_model(Challenge)
    contents = Content.objects.filter(
        object_id=challenge.pk,
        content_type=content_type
    ).order_by('-id')
    content = contents.first() if contents.exists() else None
    content_page = content.page if content else None
    page_slug = content_page.slug if content_page else None

    # Остальной код представления остается без изменений
    user_choices = ChallengeUserChoice.objects.filter(
        user=request.user,
        challenge=challenge
    ).prefetch_related('attempts__answers')

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

            if display_type == 'nothing':
                return redirect('challenge_detail', challenge_id=challenge.pk)

            elif display_type == 'text':
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
        'content_page': content_page,
        'page_slug': page_slug,
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

                if element.element == 'file':
                    uploaded_file = request.FILES.get(field_name)
                    if uploaded_file:
                        answer = ChallengeUserAnswer.objects.create(
                            attempt=attempt,
                            element=element,
                            file=uploaded_file,
                            answer=''  # пустое значение для файла
                        )
                        logger.info(f"Запускаем обработку файла в фоне, answer_id={answer.id}")
                        process_uploaded_file.delay(answer.id)
                    else:
                        logger.warning(f"Файл для поля {field_name} не был загружен")
                else:
                    answer_value = request.POST.get(field_name)
                    if answer_value is not None:
                        ChallengeUserAnswer.objects.create(
                            attempt=attempt,
                            element=element,
                            answer=answer_value
                        )

            redirect_url = reverse('challenge_view_content', kwargs={'pk': challenge.id})

            if is_ajax:
                return JsonResponse({
                    'status': 'success',
                    'message': 'Answer saved successfully!',
                    'url': redirect_url
                })
            else:
                messages.success(request, "Answer saved successfully!")
                return redirect('challenge_view_content', pk=challenge.id)

        except Exception as e:
            logger.error(f"Ошибка при сохранении ответа: {e}", exc_info=True)
            # Обработка ошибки размера файла (пример)
            if 'Uploaded file is too big' in str(e) or 'Request data too big' in str(e):
                error_message = 'File is too big: Upload your video!'
            else:
                error_message = str(e)

            if is_ajax:
                return JsonResponse({
                    'status': 'error',
                    'message': error_message,
                }, status=400)
            else:
                messages.error(request, f"url редиректа:{redirect_url}. Ошибка при сохранении: {error_message}")
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
@require_POST
def submit_challenge_in_add(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    user = request.user

    try:
        user_choice, _ = ChallengeUserChoice.objects.get_or_create(
            user=user,
            challenge=challenge
        )

        # Считаем, сколько уже было попыток ДО этой
        already_attempts_count = ChallengeUserAttempt.objects.filter(
            choice=user_choice
        ).count()

        # Создаем новую попытку
        attempt = ChallengeUserAttempt.objects.create(
            choice=user_choice,
            is_secondary=True
        )

        # Считаем сколько ответов добавляем в этой попытке
        new_answer_count = 0

        for element in challenge.elements.all():
            field_name = f"field_{element.id}"
            other_field_name = f"{field_name}_other"

            if element.element == 'file':
                uploaded_file = request.FILES.get(field_name)
                if uploaded_file:
                    ChallengeUserAnswer.objects.create(
                        attempt=attempt,
                        element=element,
                        file=uploaded_file,
                        answer=''
                    )
                    new_answer_count += 1

            elif element.element == 'checkbox':
                selected_values = request.POST.getlist(field_name)
                other_value = request.POST.get(other_field_name, "").strip()

                if "__other__" in selected_values and other_value:
                    selected_values = [v for v in selected_values if v != "__other__"]
                    selected_values.append(other_value)

                if selected_values:
                    ChallengeUserAnswer.objects.create(
                        attempt=attempt,
                        element=element,
                        answer=",".join(selected_values)
                    )
                    new_answer_count += 1

            elif element.element == 'radio':
                answer_value = request.POST.get(field_name)
                other_value = request.POST.get(other_field_name, "").strip()

                if answer_value == "__other__" and other_value:
                    answer_value = other_value

                if answer_value:
                    ChallengeUserAnswer.objects.create(
                        attempt=attempt,
                        element=element,
                        answer=answer_value
                    )
                    new_answer_count += 1

            else:  # input, textarea, date
                answer_value = request.POST.get(field_name, "").strip()
                if answer_value:
                    ChallengeUserAnswer.objects.create(
                        attempt=attempt,
                        element=element,
                        answer=answer_value
                    )
                    new_answer_count += 1

        # Считаем общее количество попыток, включая эту
        total_attempts = already_attempts_count + 1

        required_attempts = challenge.min_answers_required

        if not user_choice.is_done and total_attempts >= required_attempts:
            user_choice.is_done = True
            user_choice.save()

            user.points_count += challenge.points
            user.save()

            content_type = ContentType.objects.get_for_model(Challenge)
            content = Content.objects.filter(object_id=challenge.pk, content_type=content_type).first()
            if content:
                user.completed_content.add(content)

        return JsonResponse({
            'status': 'success',
            'message': 'Ответ успешно сохранен!',
            'url': reverse('challenge_view_content', kwargs={'pk': challenge.id})
        })

    except Exception as e:
        print(f"Error while saving the answer: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e),
        }, status=400)

@login_required
def edit_challenge_attempt(request, attempt_id):
    attempt = get_object_or_404(ChallengeUserAttempt, pk=attempt_id, choice__user=request.user)
    challenge = attempt.choice.challenge

    # Логируем начальные данные
    logger.debug(f"Attempt ID: {attempt.id}, Challenge: {challenge.title}, User: {request.user}")

    # Собираем сохранённые ответы
    answers = {}
    for ans in attempt.answers.all():
        if ans.element.element == "file" and ans.file:
            answers[ans.element.id] = {
                'value': ans.file.url,
                'basename': os.path.basename(ans.file.name)
            }
        elif ans.element.element == "checkbox":
            answers[ans.element.id] = ans.answer.split(",") if ans.answer else []
        else:
            answers[ans.element.id] = ans.answer

    logger.debug(f"Initial answers from DB: {answers}")

    elements_with_options = []
    for element in challenge.elements.filter(show_after_confirm=False):
        if element.element in ["radio", "checkbox"]:
            options = parse_radio_values(element.value)
            value = answers.get(element.id)

            field_data = {
                "element": element,
                "options": options,
                "value": None,
                "other_value": None,
            }

            if element.element == "checkbox":
                option_labels = [opt["label"] for opt in options]

                if isinstance(value, list):
                    last_value = value[-1] if value else None

                    if last_value and last_value not in option_labels:

                        known_values = [v for v in value if v in option_labels]
                        field_data["value"] = known_values + ["__other__"]
                        field_data["other_value"] = last_value
                    else:
                        field_data["value"] = value
                        field_data["other_value"] = None
                elif isinstance(value, str):
                    field_data["value"] = [value]
                    field_data["other_value"] = None
                else:
                    field_data["value"] = value
                    field_data["other_value"] = None

            elif element.element == "radio":
                option_labels = [opt["label"] for opt in options]

                field_data = {
                    "element": element,
                    "options": options,
                    "value": None,
                    "other_value": None
                }

                if value:  # Если есть значение
                    if value == "__other__":  # Случай 1: явно выбрана опция "Other"
                        field_data["value"] = "__other__"
                        field_data["other_value"] = request.POST.get(f"field_{element.id}_other", "")
                    elif value not in option_labels:  # Случай 2: значение не в списке опций
                        field_data["value"] = "__other__"
                        field_data["other_value"] = value
                    else:  # Случай 3: выбрана стандартная опция
                        field_data["value"] = value
            else:
                field_data["value"] = value

            elements_with_options.append(field_data)

        else:
            elements_with_options.append({
                "element": element,
                "options": None,
                "value": answers.get(element.id)
            })

    logger.debug(f"Final answers: {answers}")

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
        # Логируем начальные данные
        logger.debug(f"Attempt ID: {attempt.id}, Challenge: {challenge.title}, User: {request.user}")

        for element in challenge.elements.all():
            field_name = f"field_{element.id}"
            logger.debug(f"Processing element: {element.id} - {element.element}")

            if element.element == "file":
                # Обработка файлов
                uploaded_file = request.FILES.get(field_name)
                if uploaded_file:
                    logger.debug(f"File uploaded: {uploaded_file.name}")
                    answer, created = ChallengeUserAnswer.objects.get_or_create(
                        attempt=attempt,
                        element=element
                    )
                    if answer.file:
                        answer.file.delete(save=False)
                    answer.file = uploaded_file
                    answer.save()
            elif element.element == "checkbox":
                # Обработка чекбоксов
                selected_values = request.POST.getlist(field_name)
                logger.debug(f"Selected checkbox values for element {element.id}: {selected_values}")

                # Если выбрана опция "Other", проверяем введенное значение
                if "__other__" in selected_values:
                    other_value = request.POST.get(f"field_{element.id}_other")
                    logger.debug(f"Received 'Other' value for checkbox: {other_value}")

                    if other_value:  # Если введено значение для Other
                        selected_values = [v for v in selected_values if v != "__other__"]  # Убираем __other__
                        selected_values.append(other_value)  # Добавляем введенное значение
                        logger.debug(f"Saving custom 'Other' value for checkboxes: {other_value}")

                # Сохраняем выбранные значения
                answer_value = ",".join(selected_values)
                logger.debug(f"Saving checkbox answer: {answer_value}")
                ChallengeUserAnswer.objects.update_or_create(
                    attempt=attempt,
                    element=element,
                    defaults={'answer': answer_value}
                )
            elif element.element == "radio":
                # Обработка радиокнопок
                answer_value = request.POST.get(field_name)
                logger.debug(f"Received radio value: {answer_value}")

                if answer_value == "__other__":
                    logger.debug(f"Other option selected for element {element.id}")
                    other_value = request.POST.get(f"field_{element.id}_other")
                    logger.debug(f"Received 'Other' value: {other_value}")

                    if other_value:
                        answer_value = other_value  # Если пользователь ввел значение в поле Other
                        logger.debug(f"Saving custom 'Other' value: {other_value}")
                    else:
                        answer_value = "__other__"  # Если значение не введено, то сохраняем "__other__"

                logger.debug(f"Saving radio answer: {answer_value}")
                ChallengeUserAnswer.objects.update_or_create(
                    attempt=attempt,
                    element=element,
                    defaults={'answer': answer_value}
                )


            else:
                # Обработка остальных элементов
                answer_value = request.POST.get(field_name)
                if answer_value:
                    logger.debug(f"Saving other answer: {answer_value}")
                    ChallengeUserAnswer.objects.update_or_create(
                        attempt=attempt,
                        element=element,
                        defaults={'answer': answer_value}
                    )

        redirect_url = reverse('challenge_view_content', kwargs={'pk': challenge.id})
        return JsonResponse({
            'status': 'success',
            'message': 'Changes saved successfully!',
            'url': redirect_url
        })

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'status': 'error',
            'message': str(e),
        }, status=500)


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
                challenge = old_attempt.challenge

                if cancel_edit_delete:
                    new_name = f"Ответ от {timezone.now().strftime('%d.%m.%Y %H:%M')}"
                    new_attempt = ChallengeUserAttempt.objects.create(
                        user=old_attempt.user,
                        challenge=challenge,
                        is_done=is_done,
                        name=new_name
                    )

                    for answer in old_attempt.answers.all():
                        answer.pk = None
                        answer.attempt = new_attempt
                        answer.save()
                else:
                    old_attempt.is_done = is_done
                    old_attempt.save()

            return JsonResponse({'status': 'success'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


def quiz_detail(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)

    content_type = ContentType.objects.get_for_model(Quiz)
    content = Content.objects.filter(
        object_id=quiz.pk,
        content_type=content_type
    ).first()
    page_slug = content.page.slug if content and content.page else None

    total_points = sum(q.points for q in quiz.questions.all())

    return render(request, 'videos/quiz.html', {
        'quiz': quiz,
        'total_points': total_points,
        'page_slug': page_slug,  # ← Добавляем
    })


def quiz_detail_welcome(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)

    content_type = ContentType.objects.get_for_model(Quiz)
    content = Content.objects.filter(
        object_id=quiz.pk,
        content_type=content_type
    ).first()
    page_slug = content.page.slug if content and content.page else None

    total_points = sum(q.points for q in quiz.questions.all())

    return render(request, 'videos/quiz_welcome.html', {
        'quiz': quiz,
        'total_points': total_points,
        'page_slug': page_slug,  # ← Добавляем
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

    # Получаем связанный контент для этого квиза
    content_type = ContentType.objects.get_for_model(Quiz)
    contents = Content.objects.filter(
        object_id=quiz.pk,
        content_type=content_type
    ).order_by('-id')  # Сортируем, чтобы взять последнюю запись

    # Берем последнюю запись или None, если нет записей
    content = contents.first() if contents.exists() else None
    page_slug = content.page.slug if content and content.page else None
    content_page = content.page if content and content.page else None

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
            # Этот блок уже использует Content, но мы можем использовать нашу переменную content
            if content:  # Используем уже полученный content
                request.user.completed_content.add(content)
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
            'content_page': content_page,  # Добавляем страницу в контекст
            'page_slug': page_slug,
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
    quiz = question.quiz  # Получаем квиз из вопроса

    # Получаем связанный контент для этого квиза
    content_type = ContentType.objects.get_for_model(Quiz)
    contents = Content.objects.filter(
        object_id=quiz.pk,
        content_type=content_type
    ).order_by('-id')
    content = contents.first() if contents.exists() else None
    page_slug = content.page.slug if content and content.page else None
    content_page = content.page if content and content.page else None

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
    prev_question_id = question_ids[index - 1] if index > 0 else None
    next_question_id = question_ids[index + 1] if index < len(question_ids) - 1 else None

    return render(request, 'videos/quiz_review.html', {
        'question': question,
        'user_answer': user_answer.user_answer,
        'correct_answer': question.correct_answers,
        'current_index': index,
        'total_incorrect': len(question_ids),
        'quiz_id': quiz_id,
        'prev_question_id': prev_question_id,
        'next_question_id': next_question_id,
        'content_page': content_page,  # Добавляем страницу в контекст
        'page_slug': page_slug,
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

            content_type = ContentType.objects.get_for_model(Quiz)
            content = Content.objects.filter(
                object_id=quiz.pk,
                content_type=content_type
            ).first()

            if content:
                request.user.completed_content.add(content)

            # Очищаем localStorage после успешной отправки
            return JsonResponse({
                'status': 'success',
                'redirect_url': reverse('quiz_results', kwargs={'pk': quiz_id})
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)