from django.urls import path, include
from apps.users import views
from apps.users.views import get_objects
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.onboarding_view1, name='onboarding'),
    path('onboarding2/', views.onboarding_view2, name='onboarding2'),
    path('onboarding3/', views.onboarding_view3, name='onboarding3'),
    path('onboarding4/', views.onboarding_view4, name='onboarding4'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('accounts/login/', views.login_view, name='login'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('signup_complete/', views.signup_complete, name='signup_complete'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/save/', views.save_profile_steps, name='save_profile_steps'),
    path('profile_finished/', views.profile_end, name='profile_end'),
    path('auth/', include('social_django.urls', namespace='social')),  # для авторизации через Google
    path('social-auth/', include('social_django.urls', namespace='social')),
    path('redeem-reward/', views.redeem_reward, name='redeem_reward'),
    path('custom-redirect/', views.redirect_view, name='custom_redirect'),

    path('profile_page/', views.user_profile, name='user_profile'),
    path('change_profile_data/', views.user_profile_change, name='user_profile_change'),
    path('get_user_points/', views.get_user_points, name='get_user_points'),
    path('send-invite/', views.send_invite, name='send_invite'),
    path('auth/complete/google-oauth2/', views.google_oauth2_complete, name='google_oauth2_complete'),

    path('home/', views.home_view, name='home'),
    path('girl_movies/', views.reach_girl_page, name='reach_girl_page'),
    path('money_talks/', views.money_talks_page, name='money_talks_page'),
    path('you_do/', views.you_do_you_page, name='you_do_you_page'),
    path('the_levers/', views.levers_page, name='levers_page'),
    path('portfolio/', views.portfolio_page, name='portfolio_page'),
    path('get_objects/', get_objects, name='get_objects'),

    path('video/<int:video_id>/', views.video_detail, name='video_detail'),
    path('fun_fact/<int:fun_fact_id>/', views.fun_fact_detail, name='fun_fact_detail'),

    path('challenge/<int:challenge_id>/', views.challenge_detail, name='challenge_detail'),
    path('<int:challenge_id>/content/', views.challenge_detail_content, name='challenge_detail_content'),
    path('challenge/<int:pk>/add-content/', views.challenge_add_content, name='challenge_add_content'),
    path('challenge/<int:challenge_id>/submit/', views.submit_challenge, name='submit_challenge'),
    path('challenge/<int:challenge_id>/submit-in-add/', views.submit_challenge_in_add, name='submit_challenge_in_add'),
    path('challenge/<int:pk>/view/', views.challenge_view_content, name='challenge_view_content'),
    path('mark_done/<int:attempt_id>/', views.mark_done, name='mark_done'),
    path('mark_undone/<int:attempt_id>/', views.mark_undone, name='mark_undone'),
    path('delete_attempt/<int:attempt_id>/', views.delete_attempt, name='delete_attempt'),
    path('attempt/edit/<int:attempt_id>/', views.edit_challenge_attempt, name='edit_challenge_attempt'),
    path('attempt/update/<int:attempt_id>/', views.update_challenge_attempt, name='update_challenge_attempt'),
    path('save_attempts_status/', views.save_attempts_status, name='save_attempts_status'),

    path('chitchat/<int:pk>/', views.chitchat_detail, name='chitchat_detail'),
    path('content/', views.content_list, name='content_list'),
    path('success/', views.success_page, name='success_page'),
    path('chitchat/<int:pk>/submit/', views.chitchat_submit, name='chitchat_submit'),
    path('choices/<int:chit_chat_id>/', views.choice_view, name='user_choices'),

    path('quiz/<int:pk>/', views.quiz_detail, name='quiz_detail'),
    path('quiz_start/<int:pk>/', views.quiz_detail_welcome, name='quiz_detail_welcome'),
    path('quiz/<int:quiz_id>/', views.quiz_start, name='quiz_start'),
    path('quiz/<int:quiz_id>/question/<int:question_num>/', views.get_question, name='get_question'),
    path('quiz/submit/', views.submit_answer, name='submit_answer'),
    path('quiz/results/<int:pk>/', views.quiz_results, name='quiz_results'),
    path('quiz/review/start/', views.start_incorrect_review, name='start_incorrect_review'),
    path('quiz/review/<int:question_id>/<int:index>/', views.quiz_question_review, name='quiz_question_review'),
    path('quiz/<int:quiz_id>/incorrect_question/<int:index>/', views.get_incorrect_question, name='get_incorrect_question'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)