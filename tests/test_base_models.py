import pytest

from bodepontoio.models import SoftDeleteModel, TimeStampedModel
from tests.testapp.models import Article, Post


# ---------------------------------------------------------------------------
# TimeStampedModel
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTimeStampedModel:
    def test_is_abstract(self):
        assert TimeStampedModel._meta.abstract

    def test_created_at_set_on_create(self):
        obj = Article.objects.create(title="Hello")
        assert obj.created_at is not None

    def test_updated_at_changes_on_save(self):
        obj = Article.objects.create(title="Hello")
        original = obj.updated_at
        obj.title = "Updated"
        obj.save()
        obj.refresh_from_db()
        assert obj.updated_at >= original


# ---------------------------------------------------------------------------
# SoftDeleteModel
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSoftDeleteModel:
    def test_is_abstract(self):
        assert SoftDeleteModel._meta.abstract

    def test_delete_sets_deleted_at(self):
        obj = Post.objects.create(title="Gone")
        obj.delete()
        obj.refresh_from_db()
        assert obj.deleted_at is not None

    def test_is_deleted_property(self):
        obj = Post.objects.create(title="Ghost")
        assert not obj.is_deleted
        obj.delete()
        assert obj.is_deleted

    def test_default_manager_excludes_deleted(self):
        Post.objects.create(title="Visible")
        hidden = Post.objects.create(title="Hidden")
        hidden.delete()
        titles = list(Post.objects.values_list("title", flat=True))
        assert "Visible" in titles
        assert "Hidden" not in titles

    def test_all_objects_includes_deleted(self):
        Post.objects.create(title="Visible")
        hidden = Post.objects.create(title="Hidden")
        hidden.delete()
        titles = list(Post.all_objects.values_list("title", flat=True))
        assert "Visible" in titles
        assert "Hidden" in titles

    def test_restore(self):
        obj = Post.objects.create(title="Temp")
        obj.delete()
        assert Post.objects.count() == 0
        obj.restore()
        assert Post.objects.count() == 1
        assert not obj.is_deleted

    def test_hard_delete_removes_row(self):
        obj = Post.objects.create(title="Permanent")
        obj.hard_delete()
        assert Post.all_objects.count() == 0

    def test_queryset_delete_soft_deletes_all(self):
        Post.objects.create(title="A")
        Post.objects.create(title="B")
        Post.objects.all().delete()
        assert Post.objects.count() == 0
        assert Post.all_objects.count() == 2

    def test_queryset_hard_delete(self):
        Post.objects.create(title="A")
        Post.objects.create(title="B")
        Post.all_objects.hard_delete()
        assert Post.all_objects.count() == 0

    def test_queryset_alive_and_dead(self):
        Post.objects.create(title="Alive")
        dead = Post.objects.create(title="Dead")
        dead.delete()
        assert Post.all_objects.alive().count() == 1
        assert Post.all_objects.dead().count() == 1
