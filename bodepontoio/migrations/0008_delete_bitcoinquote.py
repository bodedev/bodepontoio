# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bodepontoio", "0007_alter_loginrecord_id_and_more"),
    ]

    operations = [
        migrations.DeleteModel(
            name="BitcoinQuote",
        ),
    ]
