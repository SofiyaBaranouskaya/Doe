from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from allauth.exceptions import ImmediateHttpResponse
from django.contrib import messages

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            messages.warning(request, "This Google-account is already connected to another user. Please log in instead.")
            raise ImmediateHttpResponse(redirect('login'))
