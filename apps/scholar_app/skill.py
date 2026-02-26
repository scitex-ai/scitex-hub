from apps.llm_app.skills import Skill, register

register(
    Skill(
        app_name="scholar",
        display_name="Scholar - Literature Management",
        description=(
            "Scientific literature search, bibliography management, and citation graph "
            "exploration. Users can search papers across CrossRef, OpenAlex, and Semantic "
            "Scholar. Papers can be saved to the library, organized into collections, and "
            "their citation graphs explored."
        ),
        tool_prefixes=["crossref_", "scholar_", "openalex_"],
        capabilities=[
            "Search papers by keyword, DOI, or author",
            "Manage bibliography (BibTeX import/export)",
            "Explore citation graphs (references and citations)",
            "Download and parse PDFs",
            "Enrich metadata (abstracts, impact factors, DOIs)",
            "Save papers to library collections",
        ],
        page_patterns=["/scholar/"],
        url_prefix="/scholar/",
        module_description=(
            "Literature management: search papers (CrossRef/OpenAlex/Semantic Scholar), "
            "manage bibliography, explore citation graphs, download PDFs."
        ),
        mcp_tool_examples=[
            "scholar_search_papers",
            "scholar_fetch_papers",
            "crossref_search",
        ],
    )
)
