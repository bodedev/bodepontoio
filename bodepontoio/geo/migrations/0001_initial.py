import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Regiao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=50, unique=True)),
                ("sigla", models.CharField(max_length=10, unique=True)),
            ],
            options={
                "verbose_name": "região",
                "verbose_name_plural": "regiões",
            },
        ),
        migrations.CreateModel(
            name="UF",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=50, unique=True)),
                ("sigla", models.CharField(max_length=10, unique=True)),
                (
                    "regiao",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="ufs", to="geo.regiao"
                    ),
                ),
            ],
            options={
                "verbose_name": "estado",
                "verbose_name_plural": "estados",
            },
        ),
        migrations.CreateModel(
            name="Municipio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=50)),
                (
                    "uf",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="cidades", to="geo.uf"
                    ),
                ),
            ],
            options={
                "verbose_name": "município",
                "verbose_name_plural": "municípios",
            },
        ),
    ]
