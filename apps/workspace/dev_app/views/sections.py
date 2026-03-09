"""
Design Section Views

Backward-compatible views for individual design system sections.
Each view wraps DesignSectionView with a specific section name.
"""

from .base import DesignSectionView


# Foundation views
class DesignColorsView(DesignSectionView):
    def get(self, request):
        return super().get(request, "colors")


class DesignWorkspaceColorsView(DesignSectionView):
    def get(self, request):
        return super().get(request, "workspace-colors")


class DesignWorkspaceIconsView(DesignSectionView):
    def get(self, request):
        return super().get(request, "workspace-icons")


class DesignTypographyView(DesignSectionView):
    def get(self, request):
        return super().get(request, "typography")


class DesignCodeBlocksView(DesignSectionView):
    def get(self, request):
        return super().get(request, "code-blocks")


class DesignSpacingView(DesignSectionView):
    def get(self, request):
        return super().get(request, "spacing")


class DesignThemeView(DesignSectionView):
    def get(self, request):
        return super().get(request, "theme")


class DesignGuidelinesView(DesignSectionView):
    def get(self, request):
        return super().get(request, "guidelines")


class DesignTerminalLogView(DesignSectionView):
    def get(self, request):
        return super().get(request, "terminal-log")


class DesignTerminalView(DesignSectionView):
    def get(self, request):
        return super().get(request, "terminal")


class DesignIconsView(DesignSectionView):
    def get(self, request):
        return super().get(request, "icons")


# Component views
class DesignBadgeView(DesignSectionView):
    def get(self, request):
        return super().get(request, "badge")


class DesignButtonView(DesignSectionView):
    def get(self, request):
        return super().get(request, "button")


class DesignCardView(DesignSectionView):
    def get(self, request):
        return super().get(request, "card")


class DesignCheckboxView(DesignSectionView):
    def get(self, request):
        return super().get(request, "checkbox")


class DesignFormInputView(DesignSectionView):
    def get(self, request):
        return super().get(request, "form-input")


class DesignToggleButtonCheckboxView(DesignSectionView):
    def get(self, request):
        return super().get(request, "toggle-button-checkbox")


class DesignSelectDropdownView(DesignSectionView):
    def get(self, request):
        return super().get(request, "select-dropdown")


class DesignTabsView(DesignSectionView):
    def get(self, request):
        return super().get(request, "tabs")


class DesignBreadcrumbView(DesignSectionView):
    def get(self, request):
        return super().get(request, "breadcrumb")


class DesignDropdownMenuView(DesignSectionView):
    def get(self, request):
        return super().get(request, "dropdown-menu")


class DesignFileUploadView(DesignSectionView):
    def get(self, request):
        return super().get(request, "file-upload")


class DesignSegmentedRadioControlView(DesignSectionView):
    def get(self, request):
        return super().get(request, "segmented-radio-control")


class DesignNavbarView(DesignSectionView):
    def get(self, request):
        return super().get(request, "navbar")


class DesignAlertsView(DesignSectionView):
    def get(self, request):
        return super().get(request, "alerts")


class DesignHeroView(DesignSectionView):
    def get(self, request):
        return super().get(request, "hero-guideline")


class DesignResizerView(DesignSectionView):
    def get(self, request):
        return super().get(request, "resizer")


class DesignWorkspaceLayoutView(DesignSectionView):
    def get(self, request):
        return super().get(request, "workspace-layout")


class DesignVisitorSystemView(DesignSectionView):
    def get(self, request):
        return super().get(request, "visitor-system")
