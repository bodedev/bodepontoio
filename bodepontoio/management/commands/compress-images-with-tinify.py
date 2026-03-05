import os

import tinify
from django.conf import settings
from django.core.management.base import BaseCommand

from bodepontoio.models import OptimizedImageWithTinyPNG


class Command(BaseCommand):
    help = 'Compress images in the media folder'

    def add_arguments(self, parser):
        parser.add_argument('--folders', nargs='+', required=True)

    def handle(self, *args, **options):
        tinify.key = settings.TINYPNG_KEY

        folders = options.get('folders', [])

        for folder in folders:
            try:
                print(f'Folder: {folder}')
                for root, _, files in os.walk(folder):
                    for name in files:
                        if name.endswith(('.png', '.jpg', '.jpeg')):
                            img_path = os.path.join(root, name)
                            if OptimizedImageWithTinyPNG.objects.filter(path=img_path).exists():
                                # Image already optimized. Go to next image.
                                print(f'Imagem {img_path} já foi otimizada')
                                continue
                            img_size = os.path.getsize(root + '/' + name)

                            if img_size > 250000:
                                print(f'Otimizando imagem: {img_path} com tamanho atual de {img_size}')
                                source = tinify.from_file(img_path)
                                # Resize para 1920 ou 1080 proporcional
                                resized = source.resize(method='fit', width=1920, height=1080)
                                resized.to_file(img_path)
                                new_img_size = os.path.getsize(img_path)
                                print(f'Terminou otimização imagem: {img_path} com novo tamanho de {new_img_size}')
                                OptimizedImageWithTinyPNG.objects.create(path=img_path)

            except FileNotFoundError:  # Não tem o folder especificado
                print('Não encontrou Folder/Arquivo')
