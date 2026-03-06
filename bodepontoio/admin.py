from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ConsultaCEP, LoginRecord, OptimizedImageWithTinyPNG, Pais, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active", "is_email_verified")
    search_fields = ("email", "first_name", "last_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informações pessoais", {"fields": ("first_name", "last_name")}),
        (
            "Permissões",
            {
                "fields": (
                    "is_active",
                    "is_email_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Datas importantes", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "password1", "password2"),
            },
        ),
    )


@admin.register(LoginRecord)
class LoginRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "data", "user", "ip")
    search_fields = ("user__email",)
    readonly_fields = ("user",)

    def data(self, obj):
        return obj.created_at.strftime("%d/%m/%Y %H:%M:%S")

    data.admin_order_field = "created_at"
    data.short_description = "Data/Hora"

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


@admin.register(Pais)
class PaisAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "capital", "codigo_3", "codigo_2")
    search_fields = ("nome", "capital")


@admin.register(OptimizedImageWithTinyPNG)
class OptimizedImageWithTinyPNGAdmin(admin.ModelAdmin):
    list_display = ("id", "data", "path")
    exclude = ("deleted_at", "deleted_by")

    def data(self, obj):
        return obj.created_at.strftime("%d/%m/%Y %H:%M:%S")

    data.admin_order_field = "created_at"
    data.short_description = "Data/Hora"


@admin.register(ConsultaCEP)
class ConsultaCEPAdmin(admin.ModelAdmin):
    list_display = ("id", "cep", "localidade", "uf", "localidade_slug", "fonte", "data")
    list_filter = ("uf", "fonte")
    search_fields = ("cep", "localidade", "logradouro", "bairro")
    readonly_fields = (
        "cep", "logradouro", "complemento", "bairro", "localidade", "uf",
        "ibge", "ddd", "localidade_slug", "fonte", "created_at", "updated_at",
    )

    def data(self, obj):
        return obj.created_at.strftime("%d/%m/%Y %H:%M:%S")

    data.admin_order_field = "created_at"
    data.short_description = "Data/Hora"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
