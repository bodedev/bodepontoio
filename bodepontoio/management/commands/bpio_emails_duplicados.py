from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models.functions import Lower

from bodepontoio.operations import duplicate_emails


class Command(BaseCommand):

    help = 'Lista usuários que compartilham o mesmo e-mail (ignorando maiúsculas/minúsculas).'

    def handle(self, *args, **options):
        User = get_user_model()
        duplicates = list(duplicate_emails(User._default_manager.all()))

        if not duplicates:
            self.stdout.write(self.style.SUCCESS('Nenhum e-mail duplicado encontrado.'))
            return

        for group in duplicates:
            self.stdout.write(f'{group["email_ci"]} ({group["total"]} usuários)')
            users = (
                User._default_manager.annotate(email_ci=Lower('email'))
                .filter(email_ci=group['email_ci'])
                .order_by('pk')
            )
            for user in users:
                self.stdout.write(
                    f'  id={user.pk} {User.USERNAME_FIELD}={user.get_username()!r} email={user.email!r} '
                    f'date_joined={getattr(user, "date_joined", None)} last_login={user.last_login} '
                    f'senha_utilizavel={user.has_usable_password()}'
                )

        self.stdout.write(self.style.WARNING(f'{len(duplicates)} e-mail(s) duplicado(s).'))
