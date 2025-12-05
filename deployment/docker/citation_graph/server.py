#!/usr/bin/env python3
"""FastAPI server for Citation Graph API"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import config
from service import get_service
from models import (
    CitationGraphResponse,
    RelatedPapersResponse,
    PaperSummary,
    HealthResponse,
    ErrorResponse,
)

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Service instance
service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    global service

    # Startup
    logger.info("Starting Citation Graph API...")
    try:
        config.validate_config()
        service = get_service()
        logger.info("Service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Citation Graph API...")


# Initialize FastAPI app
app = FastAPI(
    title="Citation Graph API",
    description="Citation network analysis API for research papers",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
if config.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS enabled for origins: {config.CORS_ORIGINS}")


@app.get("/", tags=["Info"])
async def root():
    """API root endpoint"""
    return {
        "name": "Citation Graph API",
        "version": "1.0.0",
        "status": "running",
        "description": "Citation network analysis for research papers",
        "endpoints": {
            "health": "/health",
            "network": "/api/network/",
            "related": "/api/related/",
            "paper": "/api/paper/",
            "cache": "/api/cache/",
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
        },
        "database": config.CROSSREF_DB_PATH,
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint

    Returns service status and database connectivity
    """
    try:
        health = service.health_check()

        if health["status"] != "healthy":
            raise HTTPException(
                status_code=503,
                detail=f"Service unhealthy: {health.get('error', 'Unknown error')}"
            )

        return health

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {str(e)}"
        )


@app.get("/api/network/", response_model=CitationGraphResponse, tags=["Citation Graph"])
async def build_network(
    doi: str = Query(..., description="Seed paper DOI"),
    top_n: int = Query(
        default=config.DEFAULT_TOP_N,
        ge=1,
        le=config.MAX_TOP_N,
        description=f"Number of related papers (max {config.MAX_TOP_N})"
    ),
    weight_coupling: float = Query(
        default=config.DEFAULT_WEIGHT_COUPLING,
        ge=0.0,
        description="Weight for bibliographic coupling"
    ),
    weight_cocitation: float = Query(
        default=config.DEFAULT_WEIGHT_COCITATION,
        ge=0.0,
        description="Weight for co-citation"
    ),
    weight_direct: float = Query(
        default=config.DEFAULT_WEIGHT_DIRECT,
        ge=0.0,
        description="Weight for direct citations"
    ),
    no_cache: bool = Query(default=False, description="Bypass cache"),
):
    """
    Build citation network for a paper

    **Algorithm**: Combines three similarity metrics:
    - **Bibliographic coupling**: Papers citing same references
    - **Co-citation**: Papers cited together
    - **Direct citations**: Papers directly connected

    **Parameters**:
    - `doi`: Seed paper DOI (required)
    - `top_n`: Number of related papers to include (default: 20, max: 100)
    - `weight_coupling`: Bibliographic coupling weight (default: 2.0)
    - `weight_cocitation`: Co-citation weight (default: 2.0)
    - `weight_direct`: Direct citation weight (default: 1.0)
    - `no_cache`: Bypass cache for fresh results

    **Example**:
    ```
    /api/network/?doi=10.1038/s41586-020-2008-3&top_n=20
    ```

    **Returns**: Graph with nodes (papers) and edges (citations)

    **Performance**: ~30s uncached, <50ms cached
    """
    try:
        logger.info(f"Building network for {doi} (top_n={top_n})")

        result = service.build_network(
            doi=doi,
            top_n=top_n,
            weight_coupling=weight_coupling,
            weight_cocitation=weight_cocitation,
            weight_direct=weight_direct,
            use_cache=not no_cache,
        )

        return result

    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Network build failed for {doi}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build citation network: {str(e)}"
        )


@app.get("/api/related/", response_model=RelatedPapersResponse, tags=["Citation Graph"])
async def get_related_papers(
    doi: str = Query(..., description="Paper DOI"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum results (max 50)"),
    no_cache: bool = Query(default=False, description="Bypass cache"),
):
    """
    Get related papers (lightweight version)

    Returns list of similar papers without full network structure.

    **Parameters**:
    - `doi`: Paper DOI (required)
    - `limit`: Maximum number of results (default: 10, max: 50)
    - `no_cache`: Bypass cache

    **Example**:
    ```
    /api/related/?doi=10.1038/s41586-020-2008-3&limit=10
    ```

    **Returns**: List of related papers with similarity scores

    **Performance**: ~15s uncached, <50ms cached
    """
    try:
        logger.info(f"Getting related papers for {doi} (limit={limit})")

        result = service.get_related_papers(
            doi=doi,
            limit=limit,
            use_cache=not no_cache,
        )

        return result

    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Related papers failed for {doi}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get related papers: {str(e)}"
        )


@app.get("/api/paper/", response_model=PaperSummary, tags=["Papers"])
async def get_paper_summary(
    doi: str = Query(..., description="Paper DOI"),
):
    """
    Get paper summary with citation counts

    Returns paper metadata and citation statistics.

    **Parameters**:
    - `doi`: Paper DOI (required)

    **Example**:
    ```
    /api/paper/?doi=10.1038/s41586-020-2008-3
    ```

    **Returns**: Paper metadata with citation/reference counts

    **Performance**: <5s
    """
    try:
        logger.info(f"Getting paper summary for {doi}")

        result = service.get_paper_summary(doi=doi)
        return result

    except ValueError as e:
        logger.warning(f"Paper not found: {doi}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Paper summary failed for {doi}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get paper summary: {str(e)}"
        )


@app.get("/api/cache/stats/", tags=["Cache"])
async def get_cache_stats():
    """
    Get cache statistics

    Returns information about cache performance:
    - Current size
    - Hit rate
    - Total hits/misses
    """
    try:
        stats = service.get_cache_stats()
        return stats
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache stats: {str(e)}"
        )


@app.post("/api/cache/clear/", tags=["Cache"])
async def clear_cache():
    """
    Clear all cached results

    **Note**: Requires service restart in production
    """
    try:
        service.clear_cache()
        return {"status": "success", "message": "Cache cleared"}
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
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

    logger.info(f"Starting Citation Graph API on {config.HOST}:{config.PORT}")
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower(),
    )
