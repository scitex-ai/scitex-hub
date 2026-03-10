from django.contrib import admin
from .models import (
    JournalPreset,
    ScientificFigure,
    FigurePanel,
    Annotation,
    FigureExport,
    FigureVersion,
)


@admin.register(JournalPreset)
class JournalPresetAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "column_type",
        "width_mm",
        "dpi",
        "font_family",
        "is_active",
    ]
    list_filter = ["column_type", "is_active"]
    search_fields = ["name"]


class FigurePanelInline(admin.TabularInline):
    model = FigurePanel
    extra = 0
    fields = ["position", "order", "source_image", "locked"]


@admin.register(ScientificFigure)
class ScientificFigureAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "layout", "status", "updated_at"]
    list_filter = ["status", "layout", "journal_preset"]
    search_fields = ["title", "description"]
    inlines = [FigurePanelInline]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(FigurePanel)
class FigurePanelAdmin(admin.ModelAdmin):
    list_display = ["position", "figure", "order", "locked", "updated_at"]
    list_filter = ["position", "locked"]
    search_fields = ["figure__title"]


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ["annotation_type", "panel", "content", "z_index", "created_at"]
    list_filter = ["annotation_type"]
    search_fields = ["content", "panel__figure__title"]


@admin.register(FigureVersion)
class FigureVersionAdmin(admin.ModelAdmin):
    list_display = [
        "figure",
        "version_type",
        "version_number",
        "label",
        "created_by",
        "created_at",
    ]
    list_filter = ["version_type", "created_at"]
    search_fields = ["figure__title", "label"]
    readonly_fields = ["id", "created_at"]


@admin.register(FigureExport)
class FigureExportAdmin(admin.ModelAdmin):
    list_display = [
        "figure",
        "format",
        "dpi",
        "status",
        "file_size_bytes",
        "created_at",
    ]
    list_filter = ["format", "status"]
    search_fields = ["figure__title"]
    readonly_fields = ["id", "created_at", "completed_at"]
