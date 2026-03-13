from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.text import slugify
from django.utils import timezone

from bodepontoio.models_managers import ComExcluidosManager, SemExcluidosManager


class BaseModel(models.Model):
    created = models.DateTimeField(editable=False, auto_now_add=True, db_index=True)
    updated = models.DateTimeField(editable=False, auto_now=True, db_index=True)

    class Meta:
        abstract = True


class Pais(BaseModel):
    nome = models.CharField(max_length=75, unique=True)
    capital = models.CharField(max_length=75, db_index=True)
    codigo_3 = models.CharField('Código 3 Dígitos', max_length=3, unique=True)
    codigo_2 = models.CharField('Código 2 Dígitos', max_length=2, unique=True)

    def __str__(self):
        return self.nome

    class Meta:
        ordering = ('nome',)
        verbose_name = 'País'
        verbose_name_plural = 'Países'


class LoginRecord(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    ip = models.GenericIPAddressField(null=True, blank=True, editable=False)

    def __str__(self):
        return str(self.user)

    class Meta:
        ordering = ('-created',)
        verbose_name = 'Login'
        verbose_name_plural = 'Logins'


class LogicDeletable(BaseModel):
    """
    Classe que fornece funcionalidade pra delete lógico de um modelo.

    Pode armazenar quem deletou e quando, também pode reativar o modelo.
    Já possui managers pra filtrar excluídos e não excluídos.
    """

    excluido = models.BooleanField(default=False, db_index=True)
    excluido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='%(class)s_excluido_por',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    excluido_em = models.DateTimeField(null=True, blank=True)

    objects = SemExcluidosManager()
    com_excluidos = ComExcluidosManager()

    def delete(self, using=None):
        self.excluido = True
        self.excluido_em = datetime.now()
        self.save()

    def logic_delete(self, user, using=None):
        self.excluido_por = user
        self.save()
        self.delete(using)

    def reativar(self):
        self.excluido = False
        self.excluido_por = None
        self.excluido_em = None
        self.save()

    class Meta:
        abstract = True


class OptimizedImageWithTinyPNG(LogicDeletable):
    path = models.CharField(max_length=255, db_index=True)

    class Meta:
        ordering = [
            '-id',
        ]
        verbose_name = 'Optimized Image With Tiny PNG'
        verbose_name_plural = 'Optimized Images With Tiny PNG'


class ConsultaCEP(BaseModel):
    """Modelo para armazenar consultas de CEP em cache."""

    cep = models.CharField("CEP", max_length=9, unique=True, db_index=True)
    logradouro = models.CharField("Logradouro", max_length=255, blank=True)
    complemento = models.CharField("Complemento", max_length=255, blank=True)
    bairro = models.CharField("Bairro", max_length=255, blank=True)
    localidade = models.CharField("Cidade", max_length=255)
    uf = models.CharField("UF", max_length=2)
    ibge = models.CharField("Código IBGE", max_length=10, blank=True)
    ddd = models.CharField("DDD", max_length=3, blank=True)
    localidade_slug = models.SlugField("Slug da Cidade", max_length=255, db_index=True)
    fonte = models.CharField(
        "Fonte",
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
        ordering = ["-created"]
        verbose_name = "Consulta CEP"
        verbose_name_plural = "Consultas CEP"

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