from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from bodepontoio.models import UserAuth


class Command(BaseCommand):

    help = 'Cria UserAuth para usuários que ainda não possuem.'

    def handle(self, *args, **options):
        User = get_user_model()
        users_without_auth = User.objects.filter(auth__isnull=True)
        count = users_without_auth.count()

        if count == 0:
            self.stdout.write('Nenhum usuário sem UserAuth encontrado.')
            return

        UserAuth.objects.bulk_create([
            UserAuth(user=user, is_email_verified=True)
            for user in users_without_auth
        ])
        self.stdout.write(self.style.SUCCESS(f'{count} UserAuth(s) criado(s) com sucesso.'))
