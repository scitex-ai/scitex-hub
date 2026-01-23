#!/usr/bin/env python3
"""FastAPI server for CrossRef Local database"""

import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
from contextlib import asynccontextmanager

import config
from database import CrossRefDatabase
from models import (
    PaperMetadata,
    CitationGraph,
    JournalMetrics,
    SearchResponse,
    HealthResponse,
    StatsResponse,
    ErrorResponse,
)

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize database connection
db = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    global db

    # Startup
    logger.info("Starting CrossRef Local API...")
    try:
        config.validate_config()
        db = CrossRefDatabase()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down CrossRef Local API...")


# Initialize FastAPI app
app = FastAPI(
    title="CrossRef Local API",
    description="Fast local CrossRef database API for research paper metadata",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", tags=["Info"])
async def root():
    """API root endpoint"""
    return {
        "name": "CrossRef Local API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "search": "/api/search/",
            "citations": "/api/citations/",
            "journal": "/api/journal/",
            "batch": "/api/batch/",
            "stats": "/api/stats/",
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint for Docker/Kubernetes

    Returns database status (fast - no expensive queries)
    """
    try:
        # Fast health check - just verify connection works
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return HealthResponse(
            status="healthy",
            database_connected=True,
            database_path=db.db_path,
            total_papers=None,  # Skip expensive count for health check
            database_size_mb=None,
            has_citations="citations" in db.tables,
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {str(e)}"
        )


@app.get("/api/search/", response_model=SearchResponse, tags=["Search"])
async def search_papers(
    doi: Optional[str] = Query(None, description="Paper DOI"),
    title: Optional[str] = Query(None, description="Title search term"),
    year: Optional[int] = Query(None, description="Publication year"),
    authors: Optional[str] = Query(None, description="Author name(s)"),
    limit: int = Query(default=10, le=100, description="Maximum results"),
):
    """
    Search for papers in local CrossRef database

    **Search Priority**: DOI > (Title + Year + Authors)

    Examples:
    - `/api/search/?doi=10.1038/nature12345`
    - `/api/search/?title=deep%20learning&year=2015`
    - `/api/search/?authors=LeCun&limit=20`
    """
    query_params = {
        "doi": doi,
        "title": title,
        "year": year,
        "authors": authors,
        "limit": limit,
    }

    try:
        if doi:
            # Direct DOI lookup (fastest)
            result = db.get_by_doi(doi)
            if result:
                return SearchResponse(
                    query=query_params,
                    results=[result],
                    total=1,
                    returned=1,
                )
            return SearchResponse(
                query=query_params,
                results=[],
                total=0,
                returned=0,
            )

        if title or authors or year:
            # Full-text search
            results = db.search_by_metadata(
                title=title,
                year=year,
                authors=authors,
                limit=limit
            )
            return SearchResponse(
                query=query_params,
                results=results,
                total=len(results),
                returned=len(results),
            )

        raise HTTPException(
            status_code=400,
            detail="Must provide at least one search parameter (doi, title, year, or authors)"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@app.get("/api/citations/", response_model=CitationGraph, tags=["Citations"])
async def get_citations(
    doi: str = Query(..., description="Paper DOI"),
    depth: int = Query(default=1, ge=1, le=3, description="Graph traversal depth"),
    include_references: bool = Query(default=True, description="Include papers this one cites"),
    include_citations: bool = Query(default=True, description="Include papers citing this one"),
):
    """
    Get citation graph for a paper

    **Parameters**:
    - `doi`: Paper DOI (required)
    - `depth`: Graph traversal depth (1-3, default: 1)
    - `include_references`: Include papers this one cites (default: true)
    - `include_citations`: Include papers citing this one (default: true)

    **Example**:
    `/api/citations/?doi=10.1038/nature12345&depth=2`

    **Returns**: Graph with nodes (papers) and edges (citations)
    """
    try:
        graph = db.get_citation_graph(
            doi=doi,
            depth=depth,
            include_references=include_references,
            include_citations=include_citations,
        )

        if graph["total_nodes"] == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Paper not found or no citation data available for DOI: {doi}"
            )

        return graph

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Citation graph error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build citation graph: {str(e)}"
        )


@app.get("/api/journal/", response_model=JournalMetrics, tags=["Journals"])
async def get_journal_info(
    issn: Optional[str] = Query(None, description="Journal ISSN"),
    name: Optional[str] = Query(None, description="Journal name"),
):
    """
    Get journal information and metrics

    **Parameters**: Provide either `issn` or `name`

    **Examples**:
    - `/api/journal/?issn=0028-0836` (Nature)
    - `/api/journal/?name=Nature`
    """
    try:
        if issn:
            journal = db.get_journal_by_issn(issn)
        elif name:
            journal = db.get_journal_by_name(name)
        else:
            raise HTTPException(
                status_code=400,
                detail="Must provide either issn or name"
            )

        if not journal:
            raise HTTPException(
                status_code=404,
                detail=f"Journal not found"
            )

        return journal

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Journal lookup error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Journal lookup failed: {str(e)}"
        )


@app.post("/api/batch/", response_model=List[PaperMetadata], tags=["Batch"])
async def batch_lookup(dois: List[str]):
    """
    Batch DOI lookup (max 100 per request)

    **Request body**: JSON array of DOIs
    ```json
    ["10.1038/nature12345", "10.1126/science.1234567"]
    ```

    **Returns**: Array of paper metadata (in same order if possible)
    """
    if len(dois) > config.MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {config.MAX_BATCH_SIZE} DOIs per batch request"
        )

    try:
        results = db.batch_get_by_dois(dois)
        return results
    except Exception as e:
        logger.error(f"Batch lookup error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch lookup failed: {str(e)}"
        )


@app.get("/api/stats/", response_model=StatsResponse, tags=["Stats"])
async def get_database_stats():
    """
    Get database statistics

    Returns information about:
    - Total papers
    - Database size
    - Year coverage
    - Available tables and indices
    - Citation data availability
    """
    try:
        stats = db.get_database_stats()
        return stats
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stats: {str(e)}"
        )


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error="Not Found",
            detail=str(exc.detail) if hasattr(exc, 'detail') else "Resource not found"
        ).dict()
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail="An unexpected error occurred"
        ).dict()
    )


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {config.HOST}:{config.PORT}")
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower(),
    )
