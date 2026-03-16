# apps/aichat/services/ai_chat.py
import requests
import logging
import json
from typing import List, Dict, Optional, Generator
from django.conf import settings
from .formatter import format_ai_response

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """
    Client for working with the OpenRouter API.
    Always uses openrouter/free for automatic selection of available free models.
    """

    # Base URL for OpenRouter API
    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str = None):
        """
        Initialize the OpenRouter client.

        Args:
            api_key: OpenRouter API key (if None, taken from settings)
        """
        self.api_key = api_key or getattr(settings, 'OPENROUTER_API_KEY', None)
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY in settings.")

        self.site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        self.site_name = getattr(settings, 'SITE_NAME', 'Investment Platform')

        # Headers for OpenRouter requests
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name,
            "Content-Type": "application/json"
        }

    def get_system_prompt(self, context: Optional[Dict] = None) -> str:
        """
        Generates the system prompt for the AI assistant.
        """
        base_prompt = (
            "You are an expert assistant on an investment learning platform. "
            "Your task is to explain complex financial concepts in simple terms, "
            "answer user questions, and guide them in their learning journey.\n\n"
            "Communication rules:\n"
            "1. Respond friendly and patiently, like an experienced mentor\n"
            "2. Use simple analogies to explain complex terms\n"
            "3. If a question goes beyond investments, gently redirect to the learning topic\n"
            "4. Always clarify that your responses are not investment advice\n"
            "5. Respond in the same language as the question\n\n"
            "Topics: investment basics, stock market, ETFs, bonds, stocks, dividends, "
            "portfolio investing, risk management, diversification."
        )

        if context:
            if context.get('topic'):
                base_prompt += f"\n\nCurrent topic the user is studying: {context['topic']}"
            if context.get('user_level'):
                base_prompt += f"\nUser level: {context['user_level']}"

        return base_prompt

    def send_message(
            self,
            user_message: str,
            conversation_history: Optional[List[Dict]] = None,
            system_prompt: Optional[str] = None,
            context: Optional[Dict] = None,
            temperature: float = 0.7,
            max_tokens: int = 1024
    ) -> Dict:
        """
        Sends a message to OpenRouter and receives a response.
        Always uses openrouter/free for automatic selection of free models.
        """
        # Build the messages list
        messages = []

        # Add system prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({"role": "system", "content": self.get_system_prompt(context)})

        # Add conversation history (last 10 messages)
        if conversation_history and isinstance(conversation_history, list):
            recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            messages.extend(recent_history)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        # Build payload - ALWAYS USE openrouter/free
        payload = {
            "model": "openrouter/free",  # <-- IMPORTANT: auto-select free model
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.9,
            "frequency_penalty": 0.3,
            "presence_penalty": 0.3,
        }

        logger.info("Sending request to OpenRouter with auto-selected free model")

        try:
            # Send request
            response = requests.post(
                url=f"{self.BASE_URL}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )

            # Check response status
            response.raise_for_status()

            # Parse response
            data = response.json()

            # Get raw content
            raw_content = data['choices'][0]['message']['content']

            # FORMAT THE RESPONSE
            formatted_content = format_ai_response(raw_content, to_html=False)

            # Extract data
            result = {
                'content': formatted_content,  # Use formatted version
                'raw_content': raw_content,    # Keep original just in case
                'model': data.get('model', 'openrouter/free'),
                'usage': data.get('usage', {}),
                'finish_reason': data['choices'][0].get('finish_reason', 'stop')
            }

            logger.info(
                f"Success! Model used: {result['model']}, Tokens: {result['usage'].get('total_tokens', 'unknown')}")
            return result

        except requests.exceptions.Timeout:
            logger.error("OpenRouter request timed out")
            return {
                'content': "Sorry, the service is temporarily unavailable. Please try again later.",
                'error': 'timeout'
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"OpenRouter HTTP error: {e.response.status_code} - {e.response.text}")

            # Special handling for 402 error (payment required)
            if e.response.status_code == 402:
                return {
                    'content': "To use this feature, please top up your balance or enable Model Training in your OpenRouter settings.",
                    'error': 'payment_required'
                }
            elif e.response.status_code == 429:
                return {
                    'content': "Daily request limit exceeded. Try again tomorrow or top up your balance to increase limits.",
                    'error': 'rate_limit'
                }

            return {
                'content': "An error occurred while contacting the AI assistant. We are already working on it.",
                'error': f'http_{e.response.status_code}'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter request failed: {e}")
            return {
                'content': "Network error occurred. Please check your connection and try again.",
                'error': 'network_error'
            }
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Unexpected OpenRouter response format: {e}")
            return {
                'content': "Received an invalid response from the AI assistant.",
                'error': 'invalid_response'
            }

    def send_message_stream(
            self,
            user_message: str,
            conversation_history: Optional[List[Dict]] = None,
            system_prompt: Optional[str] = None,
            context: Optional[Dict] = None,
            temperature: float = 0.7
    ) -> Generator[str, None, None]:
        """
        Sends a message and receives a response in streaming mode.
        Always uses openrouter/free.
        """
        # Build messages
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({"role": "system", "content": self.get_system_prompt(context)})

        if conversation_history:
            messages.extend(conversation_history[-10:])

        messages.append({"role": "user", "content": user_message})

        # Build payload with streaming enabled
        payload = {
            "model": "openrouter/free",  # <-- IMPORTANT: auto-select free model
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }

        try:
            # Send request with stream=True
            response = requests.post(
                url=f"{self.BASE_URL}/chat/completions",
                headers=self.headers,
                json=payload,
                stream=True,
                timeout=30
            )

            response.raise_for_status()

            # Process streaming response
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        if data != '[DONE]':
                            try:
                                chunk = json.loads(data)
                                if chunk['choices'][0].get('delta', {}).get('content'):
                                    yield chunk['choices'][0]['delta']['content']
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"Error receiving response: {str(e)}"


# Create a default client instance for easy import
default_client = OpenRouterClient()


# Convenient wrapper function for quick calls
def get_ai_response(
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
        context: Optional[Dict] = None
) -> str:
    """
    Simplified function to get a response from the AI.
    """
    client = OpenRouterClient()
    result = client.send_message(
        user_message=user_message,
        conversation_history=conversation_history,
        system_prompt=system_prompt,
        context=context
    )
    return result.get('content', "Sorry, unable to get a response.")