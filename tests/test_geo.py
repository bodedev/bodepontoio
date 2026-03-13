import pytest

from bodepontoio.geo.models import Municipio, Regiao, UF


@pytest.fixture
def regiao(db):
    return Regiao.objects.create(nome="Sudeste", sigla="SE")


@pytest.fixture
def uf(regiao):
    return UF.objects.create(nome="São Paulo", sigla="SP", regiao=regiao)


@pytest.fixture
def municipio(uf):
    return Municipio.objects.create(nome="Campinas", uf=uf)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRegiao:
    def test_str(self, regiao):
        assert str(regiao) == "Sudeste"

    def test_fields(self, regiao):
        assert regiao.nome == "Sudeste"
        assert regiao.sigla == "SE"

    def test_nome_unique(self, regiao):
        with pytest.raises(Exception):
            Regiao.objects.create(nome="Sudeste", sigla="XX")


@pytest.mark.django_db
class TestUF:
    def test_str(self, uf):
        assert str(uf) == "São Paulo"

    def test_fields(self, uf, regiao):
        assert uf.sigla == "SP"
        assert uf.regiao == regiao

    def test_reverse_relation(self, uf, regiao):
        assert regiao.ufs.count() == 1
        assert regiao.ufs.first() == uf


@pytest.mark.django_db
class TestMunicipio:
    def test_str(self, municipio):
        assert str(municipio) == "Campinas"

    def test_fields(self, municipio, uf):
        assert municipio.nome == "Campinas"
        assert municipio.uf == uf

    def test_reverse_relation(self, municipio, uf):
        assert uf.cidades.count() == 1
        assert uf.cidades.first() == municipio


# ---------------------------------------------------------------------------
# API — Regioes
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRegiaoViewSet:
    def test_list(self, api_client, regiao):
        response = api_client.get("/geo/regioes/")
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["nome"] == "Sudeste"
        assert response.data[0]["sigla"] == "SE"

    def test_retrieve(self, api_client, regiao):
        response = api_client.get(f"/geo/regioes/{regiao.pk}/")
        assert response.status_code == 200
        assert response.data["nome"] == "Sudeste"

    def test_retrieve_not_found(self, api_client):
        response = api_client.get("/geo/regioes/9999/")
        assert response.status_code == 404

    def test_public_no_auth_required(self, api_client, regiao):
        response = api_client.get("/geo/regioes/")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# API — UFs
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUFViewSet:
    def test_list(self, api_client, uf):
        response = api_client.get("/geo/ufs/")
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["sigla"] == "SP"

    def test_retrieve(self, api_client, uf):
        response = api_client.get(f"/geo/ufs/{uf.pk}/")
        assert response.status_code == 200
        assert response.data["nome"] == "São Paulo"
        assert response.data["regiao_id"] == uf.regiao_id

    def test_filter_by_regiao(self, api_client, regiao, uf):
        other_regiao = Regiao.objects.create(nome="Sul", sigla="S")
        UF.objects.create(nome="Paraná", sigla="PR", regiao=other_regiao)

        response = api_client.get(f"/geo/ufs/?regiao={regiao.pk}")
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["sigla"] == "SP"

    def test_filter_by_regiao_no_results(self, api_client, regiao):
        response = api_client.get("/geo/ufs/?regiao=9999")
        assert response.status_code == 200
        assert len(response.data) == 0


# ---------------------------------------------------------------------------
# API — Municipios
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMunicipioViewSet:
    def test_list(self, api_client, municipio):
        response = api_client.get("/geo/municipios/")
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["nome"] == "Campinas"

    def test_retrieve(self, api_client, municipio, uf):
        response = api_client.get(f"/geo/municipios/{municipio.pk}/")
        assert response.status_code == 200
        assert response.data["nome"] == "Campinas"
        assert response.data["uf_id"] == uf.pk

    def test_filter_by_uf(self, api_client, uf, municipio):
        other_uf = UF.objects.create(
            nome="Rio de Janeiro",
            sigla="RJ",
            regiao=uf.regiao,
        )
        Municipio.objects.create(nome="Niterói", uf=other_uf)

        response = api_client.get(f"/geo/municipios/?uf={uf.pk}")
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["nome"] == "Campinas"

    def test_filter_by_uf_no_results(self, api_client):
        response = api_client.get("/geo/municipios/?uf=9999")
        assert response.status_code == 200
        assert len(response.data) == 0
