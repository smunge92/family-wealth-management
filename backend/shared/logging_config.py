"""
Centralized logging configuration for Azure Functions.
Provides structured logging, Application Insights integration, and error correlation.
"""

import os
import logging
import uuid
import json
from datetime import datetime
from typing import Optional
import azure.functions as func
from shared.auth import get_cors_headers


def setup_logging():
    """
    Configure structured logging with Application Insights integration.
    Call this once at app startup.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Configure root logger with structured format
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    )

    # Set up Application Insights if connection string is available
    app_insights_connection = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING") or os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY")
    if app_insights_connection:
        try:
            from opencensus.ext.azure.log_exporter import AzureLogHandler
            root_logger = logging.getLogger()

            if app_insights_connection.startswith("InstrumentationKey="):
                handler = AzureLogHandler(connection_string=app_insights_connection)
            else:
                handler = AzureLogHandler(
                    connection_string=f"InstrumentationKey={app_insights_connection}"
                )

            root_logger.addHandler(handler)
            logging.getLogger(__name__).info("Application Insights logging enabled")
        except ImportError:
            logging.getLogger(__name__).warning(
                "opencensus-ext-azure not installed - Application Insights logging disabled"
            )
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to initialize Application Insights: {e}")
    else:
        logging.getLogger(__name__).info(
            "APPLICATIONINSIGHTS_CONNECTION_STRING not set - using console logging only"
        )


def generate_correlation_id() -> str:
    """Generate a short correlation ID for error tracking."""
    return uuid.uuid4().hex[:12]


def create_error_response(
    message: str,
    status_code: int = 500,
    correlation_id: Optional[str] = None
) -> func.HttpResponse:
    """
    Create a standardized error response with correlation ID.

    Args:
        message: User-facing error message
        status_code: HTTP status code
        correlation_id: Error tracking ID (auto-generated if not provided)

    Returns:
        Azure Functions HttpResponse with error details
    """
    if not correlation_id:
        correlation_id = generate_correlation_id()

    headers = get_cors_headers()

    body = {
        "error": message,
        "correlation_id": correlation_id
    }

    return func.HttpResponse(
        json.dumps(body),
        status_code=status_code,
        mimetype="application/json",
        headers=headers
    )
