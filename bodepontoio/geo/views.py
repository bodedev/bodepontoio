from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Municipio, Regiao, UF
from .serializers import MunicipioSerializer, RegiaoSerializer, UFSerializer


class RegiaoViewSet(ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = RegiaoSerializer
    queryset = Regiao.objects.all()
    pagination_class = None


class UFViewSet(ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = UFSerializer
    pagination_class = None

    def get_queryset(self):
        qs = UF.objects.all()
        regiao_id = self.request.query_params.get('regiao')
        if regiao_id:
            qs = qs.filter(regiao_id=regiao_id)
        return qs


class MunicipioViewSet(ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = MunicipioSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Municipio.objects.all()
        uf_id = self.request.query_params.get('uf')
        if uf_id:
            qs = qs.filter(uf_id=uf_id)
        return qs
