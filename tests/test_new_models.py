import pytest

from bodepontoio.models import (
    ConsultaCEP,
    LoginRecord,
    OptimizedImageWithTinyPNG,
    Pais,
    User,
)


@pytest.mark.django_db
class TestPais:
    def test_create(self):
        pais = Pais.objects.create(
            nome="Brasil", capital="Brasília", codigo_3="BRA", codigo_2="BR"
        )
        assert pais.nome == "Brasil"
        assert pais.created is not None

    def test_str(self):
        pais = Pais.objects.create(
            nome="Argentina", capital="Buenos Aires", codigo_3="ARG", codigo_2="AR"
        )
        assert str(pais) == "Argentina"

    def test_ordering(self):
        Pais.objects.create(nome="Chile", capital="Santiago", codigo_3="CHL", codigo_2="CL")
        Pais.objects.create(nome="Argentina", capital="Buenos Aires", codigo_3="ARG", codigo_2="AR")
        nomes = list(Pais.objects.values_list("nome", flat=True))
        assert nomes == ["Argentina", "Chile"]

    def test_unique_nome(self):
        Pais.objects.create(nome="Brasil", capital="Brasília", codigo_3="BRA", codigo_2="BR")
        with pytest.raises(Exception):
            Pais.objects.create(nome="Brasil", capital="Outra", codigo_3="BRB", codigo_2="BX")


@pytest.mark.django_db
class TestLoginRecord:
    def test_create(self, create_user):
        user = create_user()
        record = LoginRecord.objects.create(user=user, ip="192.168.1.1")
        assert record.user == user
        assert record.ip == "192.168.1.1"
        assert record.created is not None

    def test_str(self, create_user):
        user = create_user()
        record = LoginRecord.objects.create(user=user, ip="10.0.0.1")
        assert str(record) == str(user)

    def test_ordering(self, create_user):
        user = create_user()
        r1 = LoginRecord.objects.create(user=user, ip="1.1.1.1")
        r2 = LoginRecord.objects.create(user=user, ip="2.2.2.2")
        records = list(LoginRecord.objects.all())
        assert records[0].pk == r2.pk
        assert records[1].pk == r1.pk

    def test_user_null_on_delete(self, create_user):
        user = create_user()
        record = LoginRecord.objects.create(user=user, ip="1.1.1.1")
        user.delete()
        record.refresh_from_db()
        assert record.user is None


@pytest.mark.django_db
class TestOptimizedImageWithTinyPNG:
    def test_create(self):
        img = OptimizedImageWithTinyPNG.objects.create(path="/media/test.png")
        assert img.path == "/media/test.png"
        assert img.created is not None

    def test_soft_delete(self):
        img = OptimizedImageWithTinyPNG.objects.create(path="/media/test.png")
        img.delete()
        assert OptimizedImageWithTinyPNG.objects.count() == 0
        assert OptimizedImageWithTinyPNG.com_excluidos.count() == 1

    def test_reativar(self):
        img = OptimizedImageWithTinyPNG.objects.create(path="/media/test.png")
        img.delete()
        img.reativar()
        assert OptimizedImageWithTinyPNG.objects.count() == 1
