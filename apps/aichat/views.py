# apps/aichat/views.py
import json
import uuid
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from .models import ChatSession, ChatMessage, UserFeedback
from .services.ai_chat import OpenRouterClient

ai_client = OpenRouterClient()


class ChatView(View):
    """Основной view для отображения интерфейса чата."""
    template_name = 'aichat/chat.html'

    def get(self, request, session_id=None):
        # 🔹 Если session_id='new' или пустой — не создаём сессию
        if session_id and session_id != 'new':
            session = get_object_or_404(ChatSession, session_id=session_id)
            if session.user and session.user != request.user:
                return JsonResponse({'error': 'Access denied'}, status=403)
        else:
            session = None

        messages = []
        if session:
            messages = session.messages.all().order_by('created_at')
            # 🔹 Форматируем сообщения ассистента для отображения
            for message in messages:
                if message.role == 'assistant':
                    message.formatted_content = self._format_message(message.content)

        context = {
            'session': session,
            'messages': messages,
        }
        return render(request, self.template_name, context)

    @staticmethod
    def _format_message(text):
        """Единая функция форматирования (совпадает с JS formatMarkdown)"""
        if not text:
            return ''

        import re
        html = text

        # 🔹 Убираем множественные переносы (3+ → 2)
        html = re.sub(r'\n{3,}', '\n\n', html)

        # Заголовки
        html = re.sub(r'^### (.*$)', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.*$)', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.*$)', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # Жирный и курсив
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'__(.*?)__', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
        html = re.sub(r'_(.*?)_', r'<em>\1</em>', html)

        # Код
        html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
        html = re.sub(r'```([\s\S]*?)```', r'<pre><code>\1</code></pre>', html)

        # Цитаты
        html = re.sub(r'^> (.*$)', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)

        # Списки
        lines = html.split('\n')
        in_list = False
        list_type = None
        result = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            unordered = re.match(r'^[\*\-] (.*)$', stripped)
            ordered = re.match(r'^\d+\. (.*)$', stripped)

            if unordered or ordered:
                if not in_list:
                    if list_type:
                        result.append(f'</{list_type}>')
                    list_type = 'ul' if unordered else 'ol'
                    result.append(f'<{list_type}>')
                    in_list = True
                item = unordered.group(1) if unordered else ordered.group(1)
                result.append(f'<li>{item}</li>')
            else:
                if in_list:
                    result.append(f'</{list_type}>')
                    in_list = False
                    list_type = None
                result.append(stripped)

        if in_list:
            result.append(f'</{list_type}>')

        html = '\n'.join(result)

        # 🔹 Заменяем переносы на <br> и <p>
        html = html.replace('\n\n', '</p><p>')
        html = html.replace('\n', '<br>')

        if html and not html.startswith('<'):
            html = '<p>' + html + '</p>'
        elif html and not any(html.startswith(t) for t in ['<p>', '<h', '<ul', '<ol', '<pre', '<blockquote']):
            html = '<p>' + html + '</p>'

        # 🔹 Убираем лишние <br> и пустые <p>
        html = re.sub(r'(<br\s*/?>\s*){3,}', '<br><br>', html, flags=re.IGNORECASE)
        html = re.sub(r'<p>\s*</p>', '', html)

        return html


@require_POST
@csrf_exempt
def send_message(request, session_id):
    """API endpoint для отправки сообщения в чат."""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()

        if not user_message:
            return JsonResponse({'error': 'Message is empty'}, status=400)

        # 🔹 Если session_id='new' или пустой — создаём новую сессию с UUID
        if session_id == 'new' or not session_id:
            session = ChatSession.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_id=str(uuid.uuid4()),
                title=user_message[:17] + ('...' if len(user_message) > 17 else '')
            )
        else:
            session = get_object_or_404(ChatSession, session_id=session_id)
            # Обновляем title если он дефолтный
            if session.title == 'New Chat' or not session.title:
                session.title = user_message[:17] + ('...' if len(user_message) > 17 else '')
                session.save(update_fields=['title'])

        if session.user and session.user != request.user:
            return JsonResponse({'error': 'Access denied'}, status=403)

        # Сохраняем сообщение пользователя
        ChatMessage.objects.create(session=session, role='user', content=user_message)

        # Получаем историю для контекста
        history = session.messages.filter(role__in=['user', 'assistant']).order_by('-created_at')[:10]
        conversation_history = [{'role': m.role, 'content': m.content} for m in reversed(history)]

        # Запрос к AI
        response_data = ai_client.send_message(
            user_message=user_message,
            conversation_history=conversation_history,
            context=session.context
        )

        # Сохраняем ответ
        assistant_msg = ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=response_data.get('content', ''),
            tokens_used=response_data.get('usage', {}).get('total_tokens', 0),
            metadata={'model': response_data.get('model'), 'finish_reason': response_data.get('finish_reason')}
        )

        if 'model' in response_data and response_data['model'] != session.model_used:
            session.model_used = response_data['model']
            session.save()

        return JsonResponse({
            'status': 'success',
            'message': assistant_msg.content,
            'message_id': assistant_msg.id,
            'tokens_used': assistant_msg.tokens_used,
            'session_id': session.session_id,
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@csrf_exempt
def rate_message(request):
    try:
        data = json.loads(request.body)
        message = get_object_or_404(ChatMessage, id=data.get('message_id'))
        session = message.session
        if session.user and session.user != request.user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        UserFeedback.objects.update_or_create(
            message=message,
            defaults={'rating': data.get('rating'), 'comment': data.get('comment', '')}
        )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
def list_sessions(request):
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'sessions': []})
        sessions = ChatSession.objects.filter(user=request.user, is_active=True).order_by('-updated_at')[:50]
        return JsonResponse({
            'sessions': [{
                'session_id': s.session_id,
                'title': s.title,
                'created_at': s.created_at.isoformat(),
                'updated_at': s.updated_at.isoformat(),
                'message_count': s.get_message_count()
            } for s in sessions]
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["DELETE", "POST"])
@csrf_exempt
def delete_session(request, session_id):
    try:
        session = get_object_or_404(ChatSession, session_id=session_id)
        if session.user and session.user != request.user:
            return JsonResponse({'error': 'Access denied'}, status=403)

        next_session = None
        if request.user.is_authenticated:
            next_session = ChatSession.objects.filter(
                user=request.user, is_active=True
            ).exclude(session_id=session_id).order_by('-updated_at').first()

        session.delete()
        return JsonResponse({
            'status': 'success',
            'next_session_id': next_session.session_id if next_session else None
        })
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@csrf_exempt
def clear_history(request, session_id):
    try:
        session = get_object_or_404(ChatSession, session_id=session_id)
        if session.user and session.user != request.user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        session.messages.all().delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)