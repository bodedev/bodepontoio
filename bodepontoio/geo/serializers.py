from rest_framework import serializers

from .models import Municipio, Regiao, UF


class RegiaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Regiao
        fields = ['id', 'nome', 'sigla']


class UFSerializer(serializers.ModelSerializer):
    class Meta:
        model = UF
        fields = ['id', 'nome', 'sigla', 'regiao_id']


class MunicipioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Municipio
        fields = ['id', 'nome', 'uf_id']
