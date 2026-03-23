from django.db import models

from bodepontoio.models import BaseModel, LogicDeletable


class Article(BaseModel):
    title = models.CharField(max_length=100)

    class Meta:
        app_label = "testapp"


class Post(LogicDeletable):
    title = models.CharField(max_length=100)

    class Meta:
        app_label = "testapp"
