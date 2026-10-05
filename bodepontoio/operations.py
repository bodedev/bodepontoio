from django.conf import settings
from django.db import NotSupportedError, models
from django.db.migrations.operations.base import Operation
from django.db.models import Count, Value
from django.db.models.functions import Lower, NullIf

DEFAULT_INDEX_NAME = "bpio_user_email_ci_uniq"


def duplicate_emails(manager):
    """E-mails (em minúsculas, pela função LOWER do banco) usados por mais de um usuário.

    Ignora e-mail vazio, que o índice também não restringe. A comparação é a do
    banco: no MySQL com collation ``_ai_ci`` ela também ignora acentos, igual ao
    índice que será criado.
    """
    return (
        manager.exclude(email="")
        .annotate(email_ci=Lower("email"))
        .values("email_ci")
        .annotate(total=Count("pk"))
        .filter(total__gt=1)
        .order_by("email_ci")
    )


class AddUniqueEmailIndex(Operation):
    """Cria um índice único em ``NULLIF(LOWER(email), '')`` na tabela de usuários.

    É a única proteção real contra duas contas com o mesmo e-mail: a checagem na
    aplicação não resolve requisições simultâneas (duplo clique no cadastro, dois
    logins sem senha em paralelo). Com o índice, o segundo INSERT falha e o
    bodepontoio devolve a conta que já existe (ou "e-mail já cadastrado").

    - ``LOWER`` faz "Fulano@x.com" e "fulano@x.com" colidirem.
    - ``NULLIF(..., '')`` deixa vários usuários sem e-mail (ex.: superusuários
      criados sem e-mail): NULL não conflita em índice único. É um índice parcial
      que funciona também no MySQL, que não tem ``WHERE`` em índice.

    Funciona no SQLite, no PostgreSQL e no MySQL 8.0.13+ (índices funcionais). Não
    funciona no MariaDB. Se já houver duplicatas, a migration falha antes de
    alterar a tabela; liste-as com ``manage.py bpio_emails_duplicados``.

    Uso, numa migration do projeto::

        from django.conf import settings
        from bodepontoio.operations import AddUniqueEmailIndex

        class Migration(migrations.Migration):
            dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
            operations = [AddUniqueEmailIndex()]

    O índice fica fora do estado de models do Django (o ``auth.User`` não é do
    projeto), então o ``makemigrations`` não o enxerga nem tenta removê-lo.
    """

    reversible = True

    def __init__(self, model=None, name=DEFAULT_INDEX_NAME):
        self.model = model or settings.AUTH_USER_MODEL
        self.name = name

    def deconstruct(self):
        kwargs = {}
        if self.model != settings.AUTH_USER_MODEL:
            kwargs["model"] = self.model
        if self.name != DEFAULT_INDEX_NAME:
            kwargs["name"] = self.name
        return self.__class__.__name__, [], kwargs

    def state_forwards(self, app_label, state):
        pass

    def _constraint(self):
        return models.UniqueConstraint(NullIf(Lower("email"), Value("")), name=self.name)

    def _get_model(self, state):
        return state.apps.get_model(*self.model.split("."))

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = self._get_model(to_state)
        connection = schema_editor.connection
        if not self.allow_migrate_model(connection.alias, model):
            return
        if not connection.features.supports_expression_indexes:
            raise NotSupportedError(
                f"{connection.display_name} não suporta índices funcionais; "
                f"AddUniqueEmailIndex precisa deles (MySQL 8.0.13+, SQLite ou PostgreSQL)."
            )
        duplicates = duplicate_emails(model._default_manager.using(connection.alias))
        total = duplicates.count()
        if total:
            raise ValueError(
                f"Há {total} e-mail(s) usados por mais de um usuário em {model._meta.db_table}. "
                f"Resolva as duplicatas antes de criar o índice (liste com "
                f"`manage.py bpio_emails_duplicados`)."
            )
        schema_editor.add_constraint(model, self._constraint())

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = self._get_model(from_state)
        if not self.allow_migrate_model(schema_editor.connection.alias, model):
            return
        schema_editor.remove_constraint(model, self._constraint())

    def describe(self):
        return f"Cria o índice único {self.name} em LOWER(email) de {self.model}"

    @property
    def migration_name_fragment(self):
        return self.name.lower()
