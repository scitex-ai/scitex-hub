"""SciTeX pipeline initialization and management."""

import logging

logger = logging.getLogger(__name__)

# Global pipeline instances
_single_pipeline = None
_parallel_pipeline = None

# Availability flags
SCITEX_AVAILABLE = False
SCITEX_IMPORT_ERROR = None

try:
    from scitex.scholar.pipelines.ScholarPipelineSearchSingle import (
        ScholarPipelineSearchSingle,
    )
    from scitex.scholar.pipelines.ScholarPipelineSearchParallel import (
        ScholarPipelineSearchParallel,
    )
    SCITEX_AVAILABLE = True
except ImportError as e:
    SCITEX_AVAILABLE = False
    SCITEX_IMPORT_ERROR = str(e)
    ScholarPipelineSearchSingle = None
    ScholarPipelineSearchParallel = None


def get_single_pipeline():
    """Get or create single-database search pipeline (lazy initialization)"""
    global _single_pipeline
    
    if not SCITEX_AVAILABLE:
        return None
    
    if _single_pipeline is None:
        try:
            _single_pipeline = ScholarPipelineSearchSingle()
            logger.info("[SciTeX] Initialized single search pipeline")
        except Exception as e:
            logger.error(f"[SciTeX] Failed to initialize single pipeline: {e}")
            return None
    
    return _single_pipeline


def get_parallel_pipeline():
    """Get or create parallel multi-database search pipeline (lazy initialization)"""
    global _parallel_pipeline
    
    if not SCITEX_AVAILABLE:
        return None
    
    if _parallel_pipeline is None:
        try:
            # Create parallel pipeline with multiple databases
            _parallel_pipeline = ScholarPipelineSearchParallel()
            logger.info("[SciTeX] Initialized parallel search pipeline")
        except Exception as e:
            logger.error(f"[SciTeX] Failed to initialize parallel pipeline: {e}")
            return None
    
    return _parallel_pipeline


# EOF
