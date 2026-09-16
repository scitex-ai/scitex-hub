"""The public Design Rules docs page links the /dev/ design system only for staff.

/dev/ pages are admin-only on prod, so a link for everyone would lead
visitors to a 404.
"""

import pytest
from django.urls import reverse


@pytest.fixture
def staff_client(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="docs-staff", password="docs-staff-pass", is_staff=True
    )
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_anonymous_design_rules_page_has_no_dev_design_link(client):
    # Arrange
    path = reverse("docs_app:content", kwargs={"slug": "design-rules"})
    # Act
    html = client.get(path).content.decode()
    # Assert
    assert reverse("dev_app:design") + '"' not in html


@pytest.mark.django_db
def test_staff_design_rules_page_links_the_dev_design_system(staff_client):
    # Arrange
    path = reverse("docs_app:content", kwargs={"slug": "design-rules"})
    # Act
    html = staff_client.get(path).content.decode()
    # Assert
    assert reverse("dev_app:design") + '"' in html
