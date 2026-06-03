#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-05-22 05:15:38 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/config/logger.py
# ----------------------------------------
"""
Logger utilities for SciTeX Hub project.
Simplifies using the application-specific logger.

This module provides a convenient interface for working with Python's logging
module in the context of the SciTeX Hub project. It includes functions for
getting properly configured loggers, as well as decorators for common logging
patterns like function calls, exceptions, and API requests.
"""

import logging
from functools import wraps
import traceback
import time

# Get logger for our application
logger = logging.getLogger("scitex")


def get_logger(module_name):
    """
    Get a logger for a specific module.

    Args:
        module_name (str): Name of the module (typically __name__)

    Returns:
        logging.Logger: Logger instance with the module name prefixed with 'scitex.'
    """
    return logging.getLogger(f"scitex.{module_name}")


def log_exception(func):
    """
    Decorator to log exceptions occurring in a function.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"Exception in {func.__name__}: {str(e)}",
                exc_info=True,
                extra={"traceback": traceback.format_exc()},
            )
            raise

    return wrapper


def log_function_call(func):
    """
    Decorator to log function calls with timing information.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger.debug(f"Calling {func.__name__}")

        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"{func.__name__} completed in {elapsed:.4f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"{func.__name__} failed after {elapsed:.4f}s: {str(e)}",
                exc_info=True,
                extra={"traceback": traceback.format_exc()},
            )
            raise

    return wrapper


def log_api_request(view_func):
    """
    Decorator for logging API requests.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        start_time = time.time()
        logger.info(
            f"API Request: {request.method} {request.path} from {request.META.get('REMOTE_ADDR')}"
        )

        try:
            response = view_func(request, *args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"API Response: {response.status_code} in {elapsed:.4f}s")
            return response
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"API Error: {str(e)} after {elapsed:.4f}s",
                exc_info=True,
                extra={"traceback": traceback.format_exc()},
            )
            raise

    return wrapper


# Example usage:
# from config.logger import get_logger, log_exception, log_function_call
#
# logger = get_logger(__name__)
#
# @log_exception
# def my_function():
#     logger.info("This is an info message")
#     logger.debug("This is a debug message")
#     # ...
#
# @log_function_call
# def performance_critical_function():
#     # This will be logged with timing information
#     pass
