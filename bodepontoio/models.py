from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self, deleted_by=None):
        return self.update(deleted_at=timezone.now(), deleted_by=deleted_by)

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


AllObjectsManager = models.Manager.from_queryset(SoftDeleteQuerySet)


class TimeStampedModel(models.Model):
    """Abstract base model that adds created_at and updated_at timestamps."""

    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(TimeStampedModel):
    """Abstract base model with timestamps and soft deletion.

    - ``objects`` — default manager, excludes soft-deleted rows
    - ``all_objects`` — includes soft-deleted rows
    - ``.delete(deleted_by=user)`` sets deleted_at/deleted_by instead of removing the row
    - ``.hard_delete()`` permanently removes the row
    - ``.restore()`` clears deleted_at and deleted_by
    """

    deleted_at = models.DateTimeField("excluído em", null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="excluído por",
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, deleted_by=None):
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.save(update_fields=["deleted_at", "deleted_by"])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["deleted_at", "deleted_by"])

    @property
    def is_deleted(self):
        return self.deleted_at is not None


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("endereço de e-mail", unique=True, db_index=True)
    first_name = models.CharField("primeiro nome", max_length=150, blank=True)
    last_name = models.CharField("sobrenome", max_length=150, blank=True)
    is_active = models.BooleanField("ativo", default=True)
    is_staff = models.BooleanField("membro da equipe", default=False)
    is_email_verified = models.BooleanField("e-mail verificado", default=False)
    date_joined = models.DateTimeField("data de registro", default=timezone.now)

    groups = models.ManyToManyField(
        "auth.Group",
        blank=True,
        related_name="users",
        related_query_name="user",
        verbose_name="grupos",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        blank=True,
        related_name="users",
        related_query_name="user",
        verbose_name="permissões do usuário",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name


class Pais(TimeStampedModel):
    nome = models.CharField("nome", max_length=75, unique=True)
    capital = models.CharField("capital", max_length=75, db_index=True)
    codigo_3 = models.CharField("código 3 dígitos", max_length=3, unique=True)
    codigo_2 = models.CharField("código 2 dígitos", max_length=2, unique=True)

    def __str__(self):
        return self.nome

    class Meta:
        ordering = ("nome",)
        verbose_name = "país"
        verbose_name_plural = "países"


class LoginRecord(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="usuário",
    )
    ip = models.GenericIPAddressField("endereço IP", null=True, blank=True, editable=False)

    def __str__(self):
        return str(self.user)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "login"
        verbose_name_plural = "logins"


class ConsultaCEP(TimeStampedModel):
    cep = models.CharField("CEP", max_length=9, unique=True, db_index=True)
    logradouro = models.CharField("logradouro", max_length=255, blank=True)
    complemento = models.CharField("complemento", max_length=255, blank=True)
    bairro = models.CharField("bairro", max_length=255, blank=True)
    localidade = models.CharField("cidade", max_length=255)
    uf = models.CharField("UF", max_length=2)
    ibge = models.CharField("código IBGE", max_length=10, blank=True)
    ddd = models.CharField("DDD", max_length=3, blank=True)
    localidade_slug = models.SlugField("slug da cidade", max_length=255, db_index=True)
    fonte = models.CharField(
        "fonte",
        max_length=20,
        choices=[
            ("viacep", "ViaCEP"),
            ("awesomeapi", "AwesomeAPI"),
        ],
    )

    def save(self, *args, **kwargs):
        if not self.localidade_slug and self.localidade:
            self.localidade_slug = slugify(self.localidade)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cep} - {self.localidade}/{self.uf}"

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "consulta CEP"
        verbose_name_plural = "consultas CEP"


class OptimizedImageWithTinyPNG(SoftDeleteModel):
    path = models.CharField("caminho", max_length=255, db_index=True)

    class Meta:
        ordering = ("-id",)
        verbose_name = "imagem otimizada com TinyPNG"
        verbose_name_plural = "imagens otimizadas com TinyPNG"
