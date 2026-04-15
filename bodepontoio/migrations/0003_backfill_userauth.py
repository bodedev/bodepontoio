from django.conf import settings
from django.db import migrations


def backfill_user_auth(apps, schema_editor):
    app_label, model_name = settings.AUTH_USER_MODEL.split('.')
    User = apps.get_model(app_label, model_name)
    UserAuth = apps.get_model('bodepontoio', 'UserAuth')
    users_without_auth = User.objects.filter(auth__isnull=True)
    UserAuth.objects.bulk_create([
        UserAuth(user=user, is_email_verified=True)
        for user in users_without_auth
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('bodepontoio', '0002_userauth'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(backfill_user_auth, migrations.RunPython.noop),
    ]
