import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from bodepontoio.models import Pais


class Command(BaseCommand):

    help = 'Importa a lista de países.'

    def handle(self, *args, **options):
        csv_path = Path(__file__).resolve().parent.parent.parent / "assets" / "paises.csv"
        with open(csv_path) as handler:
            csv_reader = csv.DictReader(handler)
            for row in csv_reader:
                pais, created = Pais.objects.get_or_create(
                    nome=row['País'],
                    capital=row['Capital'],
                    codigo_3=row['3 letras'],
                    codigo_2=row['2 letras'],
                )
                self.stdout.write(f'{pais.codigo_2}: {created}')
        self.stdout.write('Fim de processo!')
