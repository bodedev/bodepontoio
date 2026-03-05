import csv

from django.core.management.base import BaseCommand

from bodepontoio.models import Pais


class Command(BaseCommand):

    help = 'Importa a lista de países.'

    def handle(self, *args, **options):
        handler = open('bodepontoio/assets/paises.csv')
        csv_reader = csv.DictReader(handler)
        for row in csv_reader:
            pais, created = Pais.objects.get_or_create(
                nome=row['País'],
                capital=row['Capital'],
                codigo_3=row['3 letras'],
                codigo_2=row['2 letras'],
            )
            print(f'{pais.codigo_2}: {created}')
        print('Fim de processo!')
