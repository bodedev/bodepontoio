from django.db import models


class SemExcluidosManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().filter(excluido=False)

    def com_excluidos(self):
        """
        Hack pra poder pegar os itens excluídos junto com os normais pelo manager padrão e por related manager.

        Funciona em código e nos templates.
        e.g.: instance.relatedmodel_set.com_excluidos
        """
        return super().get_queryset().filter(**self.core_filters)

    def soh_excluidos(self):
        """
        Hack pra poder pegar só os itens excluídos pelo manager padrão e por related manager.

        Funciona em código e nos templates.
        e.g.: instance.relatedmodel_set.soh_excluidos
        """
        return super().get_queryset().filter(id=self.instance.id).filter(excluido=True)


class ComExcluidosManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().all()
