# apps/aichat/services/formatter.py
import re
import markdown
from typing import Optional


def clean_markdown(text: str) -> str:
    """
    Очищает и форматирует Markdown-разметку.
    """
    if not text:
        return text

    # 1. Исправляем незакрытые жирные теги (**текст без закрытия)
    # Считаем количество ** в тексте
    bold_count = text.count('**')
    if bold_count % 2 != 0:  # Нечетное количество - значит где-то не закрыто
        # Добавляем закрывающий тег в конец
        text += '**'

    # 2. Исправляем незакрытые курсивные теги (* или _)
    italic_star_count = text.count('*') - (bold_count * 2)  # Звездочки, не входящие в **
    if italic_star_count % 2 != 0:
        text += '*'

    underscore_count = text.count('_')
    if underscore_count % 2 != 0:
        text += '_'

    # 3. Исправляем маркированные списки
    lines = text.split('\n')
    formatted_lines = []

    for line in lines:
        # Если строка начинается с цифры и точки, но нет пробела (например "1️⃣текст")
        if re.match(r'^\d+[️⃣]', line):
            # Добавляем пробел после эмодзи
            parts = re.split(r'([️⃣])', line, maxsplit=1)
            if len(parts) >= 3:
                line = parts[0] + parts[1] + ' ' + parts[2]

        formatted_lines.append(line)

    text = '\n'.join(formatted_lines)

    return text


def markdown_to_html(text: str) -> str:
    """
    Преобразует Markdown в безопасный HTML для отображения.
    """
    if not text:
        return ""

    # Сначала очищаем
    cleaned_text = clean_markdown(text)

    # Конвертируем Markdown в HTML
    # extensions=['extra'] включает таблицы, сноски и т.д.
    html = markdown.markdown(
        cleaned_text,
        extensions=['extra', 'nl2br'],  # nl2br превращает \n в <br>
        output_format='html5'
    )

    return html


def truncate_incomplete_sentence(text: str, max_length: Optional[int] = None) -> str:
    """
    Обрезает текст, чтобы не было оборванных предложений.
    """
    if not text:
        return text

    if max_length and len(text) > max_length:
        # Обрезаем до максимальной длины
        text = text[:max_length]

        # Ищем последнюю точку, вопросительный или восклицательный знак
        last_punct = max(
            text.rfind('.'),
            text.rfind('?'),
            text.rfind('!'),
            text.rfind('...')
        )

        if last_punct > max_length * 0.7:  # Если знак препинания не слишком рано
            text = text[:last_punct + 1]
        else:
            # Ищем последний пробел
            last_space = text.rfind(' ')
            if last_space > max_length * 0.5:
                text = text[:last_space] + '...'

    return text


def format_ai_response(text: str, to_html: bool = False) -> str:
    """
    Главная функция для форматирования ответа AI.

    Args:
        text: Исходный текст от AI
        to_html: Если True, возвращает HTML, иначе очищенный текст

    Returns:
        str: Отформатированный текст
    """
    if not text:
        return ""

    # Очищаем Markdown
    cleaned = clean_markdown(text)

    # Обрезаем незаконченные предложения (опционально)
    # cleaned = truncate_incomplete_sentence(cleaned)

    if to_html:
        return markdown_to_html(cleaned)
    else:
        return cleaned