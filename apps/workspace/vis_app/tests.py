from django.test import TestCase
from django.contrib.auth.models import User
from .models import ScientificFigure, JournalPreset, FigurePanel, Annotation


class JournalPresetTestCase(TestCase):
    def setUp(self):
        self.preset = JournalPreset.objects.create(
            name="Nature",
            column_type="single",
            width_mm=89,
            dpi=300,
            font_family="Arial",
            font_size_pt=7,
        )

    def test_preset_creation(self):
        self.assertEqual(self.preset.name, "Nature")
        self.assertEqual(self.preset.width_mm, 89)
        self.assertEqual(str(self.preset), "Nature - Single Column")


class ScientificFigureTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")

        self.figure = ScientificFigure.objects.create(
            owner=self.user,
            title="Test Figure",
            layout="2x2",
        )

    def test_figure_creation(self):
        self.assertEqual(self.figure.title, "Test Figure")
        self.assertEqual(self.figure.layout, "2x2")
        self.assertEqual(self.figure.get_panel_count(), 4)

    def test_figure_status(self):
        self.assertEqual(self.figure.status, "draft")


class FigurePanelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")

        self.figure = ScientificFigure.objects.create(
            owner=self.user, title="Test Figure"
        )

        self.panel = FigurePanel.objects.create(
            figure=self.figure, position="A", order=0
        )

    def test_panel_creation(self):
        self.assertEqual(self.panel.position, "A")
        self.assertTrue(self.panel.locked)
        self.assertEqual(str(self.panel), "Panel A - Test Figure")
