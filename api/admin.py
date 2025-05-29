from django.contrib import admin

from api.models import SourceImage, TransformedImage, User

admin.site.register(User)

admin.site.register(SourceImage)

admin.site.register(TransformedImage)
