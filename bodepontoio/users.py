from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.db import IntegrityError, transaction

# Quantas vezes tentamos criar o usuário quando o INSERT bate num unique de
# username (pego por outra requisição no meio do caminho) antes de desistir.
_MAX_CREATE_ATTEMPTS = 5


def has_username_field():
    User = get_user_model()
    try:
        User._meta.get_field("username")
    except FieldDoesNotExist:
        return False
    return True


def normalize_email(email):
    """Forma canônica do e-mail: sem espaços nas pontas e todo em minúsculas.

    O ``BaseUserManager.normalize_email`` do Django só põe o domínio em minúsculas;
    a parte local fica como veio. Com isso "Fulano@x.com" e "fulano@x.com" viram
    duas contas no SQLite e no PostgreSQL, onde ``=`` diferencia caixa (no MySQL
    com collation ``_ci`` não diferencia, e o bug fica escondido).
    """
    return (email or "").strip().lower()


def get_user_by_email(email):
    """Usuário dono do e-mail, ignorando caixa, ou ``None``.

    Usa ``iexact`` para também achar contas gravadas antes da normalização. Se o
    banco tiver duplicatas legadas, devolve sempre a mais antiga, para o fluxo ser
    determinístico em vez de estourar ``MultipleObjectsReturned``.
    """
    email = normalize_email(email)
    if not email:
        return None
    return get_user_model().objects.filter(email__iexact=email).order_by("pk").first()


def unique_username_for_email(email):
    User = get_user_model()
    base = email.split("@")[0]
    username = base
    suffix = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{suffix}"
        suffix += 1
    return username


def create_user_for_email(email, create, fields):
    """Cria o usuário de ``email`` tratando a corrida de cadastro.

    Checar se o e-mail existe e só então criar é check-then-act: duas requisições
    simultâneas (duplo clique, retry do cliente) passam juntas pela checagem e cada
    uma cria a sua conta. Só um índice único no banco fecha essa janela (ver
    ``bodepontoio.operations.AddUniqueEmailIndex``); aqui interpretamos o
    ``IntegrityError`` que ele gera:

    - se o e-mail agora existe, outra requisição ganhou a corrida: devolve
      ``(usuario_existente, False)``;
    - senão, foi o username gerado que colidiu: gera outro e tenta de novo.

    ``create(fields)`` grava o usuário e o devolve; ``fields`` já chega com o
    ``email`` normalizado e, se o modelo tiver username e ele não foi informado,
    com um username livre. Retorna ``(user, created)``.
    """
    email = normalize_email(email)
    generate_username = has_username_field() and not fields.get("username")

    for _attempt in range(_MAX_CREATE_ATTEMPTS):
        attempt_fields = {**fields, "email": email}
        if generate_username:
            attempt_fields["username"] = unique_username_for_email(email)
        try:
            with transaction.atomic():
                return create(attempt_fields), True
        except IntegrityError:
            existing = get_user_by_email(email)
            if existing is not None:
                return existing, False
            if not generate_username:
                raise

    raise IntegrityError(f"Não foi possível gerar um username livre para {email!r}.")


def _save_with_unusable_password(fields):
    user = get_user_model()(**fields)
    user.set_unusable_password()
    user.save()
    return user


def get_or_create_user_by_email(email, **extra_fields):
    user = get_user_by_email(email)
    if user is not None:
        return user, False
    return create_user_for_email(email, _save_with_unusable_password, extra_fields)
