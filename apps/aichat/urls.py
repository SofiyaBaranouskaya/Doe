from django.urls import path
from . import views

app_name = 'aichat'  # 🔹 Обязательно!

urlpatterns = [
    path('', views.ChatView.as_view(), name='chat'),
    path('<str:session_id>/', views.ChatView.as_view(), name='chat_session'),
    path('api/send/<str:session_id>/', views.send_message, name='api_send_message'),
    path('api/sessions/', views.list_sessions, name='api_list_sessions'),
    path('api/sessions/<str:session_id>/', views.delete_session, name='api_delete_session'),
    path('api/rate/', views.rate_message, name='api_rate_message'),
    path('api/clear/<str:session_id>/', views.clear_history, name='api_clear_history'),
]