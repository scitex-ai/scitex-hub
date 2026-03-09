from apps.llm_app.skills import Skill, register

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
        page_patterns=["/notebook/"],
        url_prefix="/notebook/",
        module_description=(
            "Experiment logger — proof-of-concept for platform services "
            "(DataStore, FileVault, JobQueue, scitex Bridge)."
        ),
    )
)
