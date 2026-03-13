from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from bodepontoio.models_managers import ComExcluidosManager, SemExcluidosManager
from bodepontoio.utils.cleaners import get_client_ip


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
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
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
        User,
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
        self.excluido_em = timezone.now()
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


def save_login_record(sender, user, request, **kwargs):
    client_ip = get_client_ip(request)
    LoginRecord.objects.create(
        user=user,
        ip=client_ip,
    )


user_logged_in.connect(save_login_record)


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
