"""The public Design Rules docs page links the /dev/ design system only for staff.

/dev/ is mounted only when developer tools are enabled and is staff-only, so
the link appears only for staff on a deployment where the toolbox exists.
"""

import pytest
from django.urls import reverse

from tests.apps.dev_app.dev_tools_urlconf import dev_tools_enabled_urlconf

DESIGN_LINK = 'href="/dev/design/"'


@pytest.fixture
def staff_client(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="docs-staff", password="docs-staff-pass", is_staff=True
    )
    client.force_login(user)
    return client


@pytest.fixture
def dev_tools_on(settings):
    with dev_tools_enabled_urlconf(settings):
        yield


def _design_rules(client):
    path = reverse("docs_app:content", kwargs={"slug": "design-rules"})
    return client.get(path).content.decode()


@pytest.mark.django_db
def test_anonymous_design_rules_page_has_no_dev_design_link(client, dev_tools_on):
    # Arrange
    page_client = client
    # Act
    html = _design_rules(page_client)
    # Assert
    assert DESIGN_LINK not in html


@pytest.mark.django_db
def test_staff_design_rules_page_links_the_dev_design_system(
    staff_client, dev_tools_on
):
    # Arrange
    page_client = staff_client
    # Act
    html = _design_rules(page_client)
    # Assert
    assert DESIGN_LINK in html


@pytest.mark.django_db
def test_staff_design_rules_page_has_no_link_when_dev_tools_are_off(staff_client):
    # Arrange
    page_client = staff_client
    # Act
    html = _design_rules(page_client)
    # Assert
    assert DESIGN_LINK not in html
