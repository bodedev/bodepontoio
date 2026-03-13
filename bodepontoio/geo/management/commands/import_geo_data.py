import requests
from django.core.management.base import BaseCommand
from bodepontoio.geo.models import Municipio, Regiao, UF


class Command(BaseCommand):
    help = "Importa dados geográficos do Brasil via API do IBGE"

    def handle(self, *args, **options):
        self._import_regioes()
        self._import_ufs()
        self._import_municipios()
        self.stdout.write("Fim do processo!")

    def _import_regioes(self):
        self.stdout.write("Importando regiões...")
        resp = requests.get("https://servicodados.ibge.gov.br/api/v1/localidades/regioes", timeout=30)
        resp.raise_for_status()

        for item in resp.json():
            _, created = Regiao.objects.update_or_create(
                id=item["id"],
                defaults={"nome": item["nome"], "sigla": item["sigla"]},
            )
            status = "criada" if created else "atualizada"
            self.stdout.write(f'  Região "{item["nome"]}" {status}')

    def _import_ufs(self):
        self.stdout.write("Importando estados...")

        regioes = Regiao.objects.all()

        for regiao in regioes:
            resp = requests.get(
                f"https://servicodados.ibge.gov.br/api/v1/localidades/regioes/{regiao.id}/estados",
                timeout=30,
            )
            resp.raise_for_status()

            for item in resp.json():
                _, created = UF.objects.update_or_create(
                    id=item["id"],
                    defaults={"nome": item["nome"], "regiao": regiao, "sigla": item["sigla"]},
                )
                status = "criado" if created else "atualizado"
                self.stdout.write(f'  Estado "{item["nome"]}" {status}')

    def _import_municipios(self):
        self.stdout.write("Importando municípios...")

        ufs = UF.objects.all()

        for uf in ufs:
            resp = requests.get(
                f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf.id}/municipios",
                timeout=30,
            )
            resp.raise_for_status()

            municipios = resp.json()
            self.stdout.write(f"  {uf.sigla}: {len(municipios)} municípios")
            for item in municipios:
                Municipio.objects.update_or_create(
                    id=item["id"],
                    defaults={"nome": item["nome"], "uf": uf},
                )
