import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from garden.models import Garden, Plant

pytestmark = pytest.mark.django_db


@pytest.fixture
def mom(db):
    return User.objects.create_user("becky")


@pytest.fixture
def dad(db):
    return User.objects.create_user("dad")


def test_invite_grants_access_and_switch_changes_view(client, mom, dad):
    Plant.objects.create(common_name="Moms Rose", garden=Garden.for_user(mom))
    Plant.objects.create(common_name="Dads Fern", garden=Garden.for_user(dad))

    client.force_login(mom)
    client.post(reverse("garden-invite"), {"username": "DAD"})  # case-insensitive
    assert Garden.for_user(mom).members.filter(pk=dad.pk).exists()

    client.force_login(dad)
    r = client.get(reverse("plant-list"))
    assert b"Dads Fern" in r.content and b"Moms Rose" not in r.content

    client.post(reverse("garden-switch"), {"garden": Garden.for_user(mom).pk})
    r = client.get(reverse("plant-list"))
    assert b"Moms Rose" in r.content and b"Dads Fern" not in r.content


def test_uninvited_switch_is_refused(client, mom, dad):
    Plant.objects.create(common_name="Moms Rose", garden=Garden.for_user(mom))
    client.force_login(dad)
    client.post(reverse("garden-switch"), {"garden": Garden.for_user(mom).pk})
    r = client.get(reverse("plant-list"))
    assert b"Moms Rose" not in r.content


def test_revocation_ends_access_even_mid_session(client, mom, dad):
    Plant.objects.create(common_name="Moms Rose", garden=Garden.for_user(mom))
    Garden.for_user(mom).members.add(dad)
    client.force_login(dad)
    client.post(reverse("garden-switch"), {"garden": Garden.for_user(mom).pk})
    assert b"Moms Rose" in client.get(reverse("plant-list")).content

    Garden.for_user(mom).members.remove(dad)
    r = client.get(reverse("plant-list"))  # stale session selection falls back
    assert b"Moms Rose" not in r.content and r.status_code == 200


def test_member_creates_into_the_shared_garden(client, mom, dad):
    Garden.for_user(mom).members.add(dad)
    client.force_login(dad)
    client.post(reverse("garden-switch"), {"garden": Garden.for_user(mom).pk})
    client.post(reverse("plant-add"), {"common_name": "Dads Gift Dahlia",
                                       "planted_precision": "exact", "is_ornamental": "on"})
    plant = Plant.objects.get(common_name="Dads Gift Dahlia")
    assert plant.garden == Garden.for_user(mom)
    # mom sees it
    client.force_login(mom)
    assert b"Dads Gift Dahlia" in client.get(reverse("plant-list")).content


def test_media_isolated_but_shared_when_member(client, mom, dad, settings, tmp_path):
    import io

    from PIL import Image

    from garden.models import Photo

    # serve() reads the filesystem; give this test real files, not the
    # suite's in-memory storage.
    settings.MEDIA_ROOT = str(tmp_path)
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    }
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "green").save(buf, "PNG")
    from django.core.files.base import ContentFile

    photo = Photo(garden=Garden.for_user(mom))
    photo.file.save("moms-secret.png", ContentFile(buf.getvalue()), save=True)

    client.force_login(dad)
    assert client.get(f"/media/{photo.file.name}").status_code == 404
    Garden.for_user(mom).members.add(dad)
    assert client.get(f"/media/{photo.file.name}").status_code == 200


def test_only_owner_manages_members(client, mom, dad):
    Garden.for_user(mom).members.add(dad)
    client.force_login(dad)
    # dad inviting someone affects DAD's garden, not mom's
    other = User.objects.create_user("stranger")
    client.post(reverse("garden-invite"), {"username": "stranger"})
    assert not Garden.for_user(mom).members.filter(pk=other.pk).exists()
    assert Garden.for_user(dad).members.filter(pk=other.pk).exists()
