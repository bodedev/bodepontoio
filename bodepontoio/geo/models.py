from django.db import models


class Regiao(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    sigla = models.CharField(max_length=10, unique=True)

    class Meta:
        verbose_name = 'região'
        verbose_name_plural = 'regiões'

    def __str__(self):
        return self.nome


class UF(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    sigla = models.CharField(max_length=10, unique=True)
    regiao = models.ForeignKey(Regiao, on_delete=models.CASCADE, related_name='ufs')

    class Meta:
        verbose_name = 'estado'
        verbose_name_plural = 'estados'

    def __str__(self):
        return self.nome


class Municipio(models.Model):
    nome = models.CharField(max_length=50)
    uf = models.ForeignKey(UF, on_delete=models.CASCADE, related_name='cidades')

    class Meta:
        verbose_name = 'município'
        verbose_name_plural = 'municípios'

    def __str__(self):
        return self.nome
