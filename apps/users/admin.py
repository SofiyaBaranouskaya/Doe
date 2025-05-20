from django.contrib import admin
from social_django.models import Association, Nonce
from django.contrib.auth.models import Group

admin.site.unregister(Group)
admin.site.unregister(Association)
admin.site.unregister(Nonce)