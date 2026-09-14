#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apps we plan to build, shown on Home as "Coming soon" tiles (the roadmap).

A placeholder disappears by itself once a real app with the same id is
registered, published or installed (see ``visible_planned_apps``).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlannedApp:
    id: str
    name_en: str
    name_ja: str
    icon: str
    group: str
    category: str
    description_en: str
    description_ja: str
    # Starter brief for the create flow (#859): what the app is for, its core
    # screens, and the data it reads or writes. English: it is agent-facing.
    purpose: str = ""
    screens: str = ""
    data: str = ""

    @property
    def brief(self) -> str:
        return (
            f"Purpose: {self.purpose}\nCore screens: {self.screens}\n"
            f"Data: {self.data}"
        )

    def name(self, language: str) -> str:
        return self.name_ja if language.startswith("ja") else self.name_en

    def description(self, language: str) -> str:
        return self.description_ja if language.startswith("ja") else self.description_en


PLANNED_APPS: tuple[PlannedApp, ...] = (
    PlannedApp(
        "files",
        "Files",
        "ファイル",
        "fas fa-folder-open",
        "foundation",
        "data",
        "Browse, upload and share the files in your projects.",
        "プロジェクトのファイルを閲覧・アップロード・共有します。",
        purpose="A file browser for everything in the user's projects.",
        screens="project tree; file preview (text, image, PDF, CSV); upload and share dialog.",
        data="reads and writes files in the project directory; share links are per file.",
    ),
    PlannedApp(
        "stats",
        "Stats",
        "統計",
        "fas fa-chart-bar",
        "work",
        "analysis",
        "Run statistical tests and report them in publication style.",
        "統計検定を実行し、論文形式で結果を報告します。",
        purpose="Run statistical tests on project data and report them in publication style.",
        screens="pick a data file and columns; choose a test; results table with effect sizes; export.",
        data="reads CSV files under data/; writes reports under results/stats/.",
    ),
    PlannedApp(
        "grant-writer",
        "Grant Writer",
        "申請書ライター",
        "fas fa-file-signature",
        "work",
        "writing",
        "Draft grant proposals from your projects and publications.",
        "プロジェクトと業績から研究費の申請書を作成します。",
        purpose="Draft a grant proposal from the user's projects, papers and CV.",
        screens="call picker with its sections; section editor with AI drafts; budget table; PDF export.",
        data="reads project manuscripts, references.bib and the profile; writes a proposal under grants/.",
    ),
    PlannedApp(
        "slides",
        "Slides",
        "スライド",
        "fas fa-chalkboard",
        "publish",
        "visualization",
        "Build talk slides from your figures and manuscripts.",
        "図や原稿から発表用スライドを作成します。",
        purpose="Build talk slides from the project's figures and manuscript.",
        screens="deck list; Markdown slide editor with live preview; figure picker; PDF export.",
        data="reads figures/ and references.bib; writes Markdown decks under slides/.",
    ),
    PlannedApp(
        "mail",
        "Mail",
        "メール",
        "fas fa-envelope",
        "work",
        "social",
        "Read and write research email next to your projects.",
        "プロジェクトの隣で研究のメールを読み書きします。",
        purpose="Read and write research email next to the project it concerns.",
        screens="inbox filtered by project; thread view; compose with attachments from the project.",
        data="reads and sends mail through the user's connected account; links threads to projects.",
    ),
    PlannedApp(
        "screen-recorder",
        "Screen Recorder",
        "画面録画",
        "fas fa-video",
        "work",
        "utility",
        "Record your screen for demos, tutorials and lab notes.",
        "デモ・チュートリアル・実験ノート用に画面を録画します。",
        purpose="Record the screen for demos, tutorials and lab notes.",
        screens="record controls (screen, window, microphone); recordings list; trim and caption view.",
        data="writes video files under recordings/ in the project; reads nothing else.",
    ),
    PlannedApp(
        "live-paper",
        "Live Paper",
        "ライブペーパー",
        "fas fa-newspaper",
        "publish",
        "writing",
        "Publish a paper whose figures and numbers stay live with the data.",
        "図や数値がデータと連動し続ける論文を公開します。",
        purpose="Publish a paper whose figures and numbers stay live with the data.",
        screens="paper view with live figures; data provenance panel; publish and version history.",
        data="reads the manuscript, figures and data files; writes a published snapshot per version.",
    ),
    PlannedApp(
        "agentic-journal",
        "Agentic Journal",
        "エージェンティックジャーナル",
        "fas fa-book-open",
        "publish",
        "reference",
        "A journal where agents help review and reproduce submissions.",
        "エージェントが査読と再現を手伝うジャーナルです。",
        purpose="A journal where agents help review and reproduce submissions.",
        screens="submission form; reviewer dashboard with agent reproduction reports; decision view.",
        data="reads submitted manuscripts, code and data; writes reviews and reproduction logs.",
    ),
)

PLANNED_BY_ID = {app.id: app for app in PLANNED_APPS}


def canonical_app_id(name: str) -> str:
    """Store slugs vary ("scitex_live_paper_app"); compare them as "live-paper"."""
    slug = name.strip().lower().replace("_", "-").removeprefix("scitex-")
    for suffix in ("-app", "-hub"):
        slug = slug.removesuffix(suffix)
    return slug


def visible_planned_apps(real_app_names) -> list[PlannedApp]:
    """The planned apps that no real app has replaced yet."""
    taken = {canonical_app_id(name) for name in real_app_names}
    return [app for app in PLANNED_APPS if app.id not in taken]


# EOF
