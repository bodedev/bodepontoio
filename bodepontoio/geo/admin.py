from django.contrib import admin

from .models import Municipio, Regiao, UF

admin.site.register(Regiao)
admin.site.register(UF)
admin.site.register(Municipio)
