import pytest

from bodepontoio.models import BaseModel, LogicDeletable
from bodepontoio.tests.testapp.models import Article, Post

# ---------------------------------------------------------------------------
# BaseModel
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBaseModel:
    def test_is_abstract(self):
        assert BaseModel._meta.abstract

    def test_created_set_on_create(self):
        obj = Article.objects.create(title="Hello")
        assert obj.created is not None

    def test_updated_changes_on_save(self):
        obj = Article.objects.create(title="Hello")
        original = obj.updated
        obj.title = "Updated"
        obj.save()
        obj.refresh_from_db()
        assert obj.updated >= original


# ---------------------------------------------------------------------------
# LogicDeletable
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLogicDeletable:
    def test_is_abstract(self):
        assert LogicDeletable._meta.abstract

    def test_delete_sets_excluido(self):
        obj = Post.objects.create(title="Gone")
        obj.delete()
        obj.refresh_from_db()
        assert obj.excluido is True

    def test_delete_sets_excluido_em(self):
        obj = Post.objects.create(title="Gone")
        obj.delete()
        obj.refresh_from_db()
        assert obj.excluido_em is not None

    def test_default_manager_excludes_deleted(self):
        Post.objects.create(title="Visible")
        hidden = Post.com_excluidos.create(title="Hidden")
        hidden.delete()
        titles = list(Post.objects.values_list("title", flat=True))
        assert "Visible" in titles
        assert "Hidden" not in titles

    def test_com_excluidos_includes_deleted(self):
        Post.objects.create(title="Visible")
        hidden = Post.com_excluidos.create(title="Hidden")
        hidden.delete()
        titles = list(Post.com_excluidos.values_list("title", flat=True))
        assert "Visible" in titles
        assert "Hidden" in titles

    def test_reativar(self):
        obj = Post.objects.create(title="Temp")
        obj.delete()
        assert Post.objects.count() == 0
        obj.reativar()
        assert Post.objects.count() == 1
        assert obj.excluido is False

    def test_reativar_clears_excluido_por(self, create_user):
        user = create_user(email="restorer@example.com")
        obj = Post.objects.create(title="Restored")
        obj.logic_delete(user)
        obj.reativar()
        obj.refresh_from_db()
        assert obj.excluido_por is None
        assert obj.excluido_em is None

    def test_logic_delete_records_excluido_por(self, create_user):
        user = create_user(email="deleter@example.com")
        obj = Post.objects.create(title="Tracked")
        obj.logic_delete(user)
        obj.refresh_from_db()
        assert obj.excluido_por == user

    def test_delete_without_user_leaves_excluido_por_null(self):
        obj = Post.objects.create(title="Anonymous")
        obj.delete()
        obj.refresh_from_db()
        assert obj.excluido_por is None

    def test_com_excluidos_method_on_default_manager(self):
        """
        Regressão: Model.objects.com_excluidos() lançava AttributeError
        ('core_filters' inexistente) porque `objects` não é um related
        manager. Ver Sentry BODDIT-BACKEND-Q.
        """
        Post.objects.create(title="Visible")
        hidden = Post.com_excluidos.create(title="Hidden")
        hidden.delete()
        titles = list(Post.objects.com_excluidos().values_list("title", flat=True))
        assert "Visible" in titles
        assert "Hidden" in titles

    def test_com_excluidos_method_on_related_manager_uses_core_filters(self, create_user):
        """
        Confirma que com_excluidos() filtra pelo FK real (core_filters) e não
        por coincidência de ids: cria um Post decoy cujo id colide com o do
        owner mas que não pertence a ele, pra garantir que o teste falharia
        se a filtragem estivesse errada.
        """
        owner = create_user(email="owner@example.com")
        Post.objects.create(id=owner.id, title="Decoy")
        mine = Post.objects.create(title="Mine")
        mine.excluido_por = owner
        mine.delete()
        titles = list(owner.post_excluido_por.com_excluidos().values_list("title", flat=True))
        assert titles == ["Mine"]
        assert "Decoy" not in titles

    def test_soh_excluidos_method_on_default_manager(self):
        """
        Regressão: mesmo padrão de bug do com_excluidos (Sentry BODDIT-BACKEND-Q),
        Model.objects.soh_excluidos() lançava AttributeError ('instance' inexistente)
        fora de um related manager.
        """
        Post.objects.create(title="Visible")
        hidden = Post.com_excluidos.create(title="Hidden")
        hidden.delete()
        titles = list(Post.objects.soh_excluidos().values_list("title", flat=True))
        assert titles == ["Hidden"]

    def test_soh_excluidos_method_on_related_manager_uses_core_filters(self, create_user):
        """
        Regressão: soh_excluidos() usava `filter(id=self.instance.id)` — um
        copy-paste que comparava o id do Post com o id do usuário pai, em vez
        de `**self.core_filters` (o FK correto). O Post decoy tem o id igual
        ao do owner e está excluído, mas não pertence a ele: só passa no
        filtro antigo (buggy), nunca no correto.
        """
        owner = create_user(email="owner2@example.com")
        decoy = Post.objects.create(id=owner.id, title="Decoy")
        decoy.delete()
        mine = Post.objects.create(title="Mine")
        mine.excluido_por = owner
        mine.delete()
        titles = list(owner.post_excluido_por.soh_excluidos().values_list("title", flat=True))
        assert titles == ["Mine"]
        assert "Decoy" not in titles
