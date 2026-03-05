from django.contrib import admin

from bodepontoio.models import ConsultaCEP, LoginRecord, OptimizedImageWithTinyPNG, Pais

FORMATO_DATA_HORA_PADRAO_ADMIN = '%d/%m/%Y %H:%M:%S'
FORMATO_DATA_SIMPLIFICADO = "%d/%m/%Y"


class BaseExcludeLogicDeleted(admin.ModelAdmin):
    exclude = (
        'excluido',
        'excluido_por',
        'excluido_em',
    )


class LoginRecordAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'data',
        'user',
        'ip',
    )
    search_fields = (
        'user__email',
        'user__username',
    )
    readonly_fields = ('user',)

    def data(self, obj):
        return obj.created.strftime('%d/%m/%Y %H:%M:%S')

    data.admin_order_field = 'created'
    data.short_description = 'Data/Hora'

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


class PaisAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nome',
        'capital',
        'codigo_3',
        'codigo_2',
    )
    search_fields = (
        'nome',
        'capital',
    )


class OptimizedImageWithTinyPNGAdmin(BaseExcludeLogicDeleted):
    list_display = (
        'id',
        'data',
        'path',
    )

    def data(self, obj):
        return obj.created.strftime('%d/%m/%Y %H:%M:%S')

    data.admin_order_field = 'created'
    data.short_description = 'Data/Hora'


class ConsultaCEPAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cep",
        "localidade",
        "uf",
        "localidade_slug",
        "fonte",
        "data",
    )
    list_filter = ("uf", "fonte")
    search_fields = ("cep", "localidade", "logradouro", "bairro")
    readonly_fields = ("cep", "logradouro", "complemento", "bairro", "localidade", "uf", "ibge", "ddd", "localidade_slug", "fonte", "created", "updated")

    def data(self, obj):
        return obj.created.strftime("%d/%m/%Y %H:%M:%S")

    data.admin_order_field = "created"
    data.short_description = "Data/Hora"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(ConsultaCEP, ConsultaCEPAdmin)
admin.site.register(LoginRecord, LoginRecordAdmin)
admin.site.register(OptimizedImageWithTinyPNG, OptimizedImageWithTinyPNGAdmin)
admin.site.register(Pais, PaisAdmin)
