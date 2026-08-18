from apps.infra.llm_app.skills import Skill, register

register(
    Skill(
        app_name="notebook",
        display_name="Lab Notebook",
        description=(
            "Simple experiment logger proving platform services work: "
            "DataStore for structured experiment records, FileVault for CSV exports, "
            "JobQueue for async processing, and scitex Bridge for io operations."
        ),
        capabilities=[
            "Log experiments with structured metadata (title, date, status, notes, tags)",
            "Export experiment data to CSV via background job",
        ],
        # No url_route: notebook_app is not mounted in config/urls.py at all.
        # It previously advertised "/notebook/", which only 301-redirects to
        # /apps/notebook/ — and that 404s. An app with no mount must not be
        # advertised, so it is omitted from the assistant's module list.
        url_route="",
        module_description=(
            "Experiment logger — proof-of-concept for platform services "
            "(DataStore, FileVault, JobQueue, scitex Bridge)."
        ),
    )
)
