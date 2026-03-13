from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MunicipioViewSet, RegiaoViewSet, UFViewSet

router = DefaultRouter()
router.register(r'regioes', RegiaoViewSet, basename='regiao')
router.register(r'ufs', UFViewSet, basename='uf')
router.register(r'municipios', MunicipioViewSet, basename='municipio')

urlpatterns = [
    path('', include(router.urls)),
]
