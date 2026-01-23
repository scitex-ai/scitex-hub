#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Port Proxy Utility

Simple HTTP proxy for forwarding requests to localhost services on custom ports.
Used for TensorBoard, Jupyter, MLflow, and other project services.
"""

import logging
import requests
from django.http import HttpResponse, StreamingHttpResponse
from django.core.exceptions import PermissionDenied, ValidationError

logger = logging.getLogger(__name__)


class PortProxyManager:
    """Manage HTTP proxying to localhost services."""

    # Allowed port range for services
    MIN_PORT = 10000
    MAX_PORT = 20000

    def validate_port(self, port: int) -> bool:
        """
        Validate port is in allowed range.

        Args:
            port: Port number to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If port is invalid
        """
        if not isinstance(port, int):
            raise ValidationError(f"Port must be an integer, got {type(port)}")

        if port < self.MIN_PORT or port > self.MAX_PORT:
            raise ValidationError(
                f"Port {port} is outside allowed range ({self.MIN_PORT}-{self.MAX_PORT})"
            )

        return True

    def proxy_request(self, request, port: int) -> HttpResponse:
        """
        Proxy an HTTP request to a localhost service.

        Args:
            request: Django request object
            port: Target port number

        Returns:
            HttpResponse with proxied content

        Raises:
            ValidationError: If port is invalid
            PermissionDenied: If access is not allowed
        """
        # Validate port
        self.validate_port(port)

        # Build target URL
        target_url = f"http://127.0.0.1:{port}{request.path}"
        if request.META.get('QUERY_STRING'):
            # Remove 'port' parameter from query string to avoid confusion
            query_params = []
            for param in request.META['QUERY_STRING'].split('&'):
                if not param.startswith('port='):
                    query_params.append(param)
            if query_params:
                target_url += '?' + '&'.join(query_params)

        logger.debug(f"Proxying request to: {target_url}")

        try:
            # Forward the request
            proxied_response = requests.request(
                method=request.method,
                url=target_url,
                headers={
                    key: value for key, value in request.headers.items()
                    if key.lower() not in ['host', 'connection']
                },
                data=request.body if request.method in ['POST', 'PUT', 'PATCH'] else None,
                cookies=request.COOKIES,
                allow_redirects=False,
                stream=True,
                timeout=30
            )

            # Handle redirects by updating Location header
            if 300 <= proxied_response.status_code < 400:
                location = proxied_response.headers.get('Location', '')
                if location.startswith(f'http://127.0.0.1:{port}'):
                    # Replace with our proxy URL
                    location = location.replace(
                        f'http://127.0.0.1:{port}',
                        f'{request.scheme}://{request.get_host()}{request.path}?port={port}'
                    )

                response = HttpResponse(
                    status=proxied_response.status_code,
                    content=proxied_response.content
                )
                response['Location'] = location
                return response

            # For streaming responses (like TensorBoard)
            if proxied_response.headers.get('content-type', '').startswith('text/event-stream'):
                response = StreamingHttpResponse(
                    proxied_response.iter_content(chunk_size=8192),
                    content_type=proxied_response.headers.get('content-type'),
                    status=proxied_response.status_code
                )
            else:
                # Regular response
                response = HttpResponse(
                    content=proxied_response.content,
                    status=proxied_response.status_code,
                    content_type=proxied_response.headers.get('content-type', 'text/html')
                )

            # Copy relevant headers
            excluded_headers = [
                'connection', 'keep-alive', 'proxy-authenticate',
                'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade'
            ]

            for header, value in proxied_response.headers.items():
                if header.lower() not in excluded_headers:
                    response[header] = value

            return response

        except requests.exceptions.ConnectionError:
            return HttpResponse(
                f"""
                <html>
                <head><title>Service Not Running</title></head>
                <body>
                    <h1>Service Not Running</h1>
                    <p>No service is running on port {port}.</p>
                    <p>Please start your service (TensorBoard, Jupyter, etc.) and try again.</p>
                    <pre>Example: tensorboard --logdir=./logs --port={port} --host=127.0.0.1</pre>
                </body>
                </html>
                """,
                status=503,
                content_type='text/html'
            )
        except requests.exceptions.Timeout:
            return HttpResponse(
                f"Service on port {port} timed out",
                status=504,
                content_type='text/plain'
            )
        except Exception as e:
            logger.error(f"Error proxying to port {port}: {e}", exc_info=True)
            return HttpResponse(
                f"Error connecting to service: {str(e)}",
                status=500,
                content_type='text/plain'
            )


def get_port_proxy_manager():
    """Get port proxy manager instance."""
    return PortProxyManager()


# EOF
