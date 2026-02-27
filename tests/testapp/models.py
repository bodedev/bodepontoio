from django.db import models

from bodepontoio.models import SoftDeleteModel, TimeStampedModel


class Article(TimeStampedModel):
    title = models.CharField(max_length=100)

    class Meta:
        app_label = "testapp"


class Post(SoftDeleteModel):
    title = models.CharField(max_length=100)

    class Meta:
        app_label = "testapp"
