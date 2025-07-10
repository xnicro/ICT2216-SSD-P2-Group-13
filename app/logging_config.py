import logging
import os
from pygelf import GelfUdpHandler
import socket
from datetime import datetime
import re

# Global variable to store the Graylog handler
_graylog_handler = None


def sanitize_log_input(value):
    """Sanitize input to prevent log injection attacks"""
    if value is None:
        return None
    
    # Convert to string if not already
    value_str = str(value)
    
    # Remove or escape potentially dangerous characters
    # Remove newlines, carriage returns, and other control characters
    value_str = re.sub(r'[\r\n\t\x00-\x1f\x7f-\x9f]', '', value_str)
    
    return value_str


def sanitize_dict(data, sanitize_keys=False):
    """Recursively sanitize all string values in a dictionary"""
    if data is None:
        return None
    
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # Sanitize keys if requested (for untrusted dictionary keys)
            safe_key = sanitize_log_input(str(key)) if sanitize_keys else key
            result[safe_key] = sanitize_dict(value, sanitize_keys)
        return result
    elif isinstance(data, list):
        return [sanitize_dict(item, sanitize_keys) for item in data]
    elif isinstance(data, str):
        return sanitize_log_input(data)
    else:
        # For non-string types (int, float, bool, etc.), convert to string and sanitize
        return sanitize_log_input(str(data))


def setup_graylog_logging(app):
    """Configure Graylog logging for Flask application"""
    global _graylog_handler

    # Get Graylog configuration from environment
    graylog_host = os.getenv('GRAYLOG_HOST', 'localhost')
    graylog_port = int(os.getenv('GRAYLOG_PORT', 12201))
    app_name = os.getenv('APP_NAME', 'SITSecure')

    try:
        # Create Graylog handler
        _graylog_handler = GelfUdpHandler(
            host=graylog_host,
            port=graylog_port,
            facility=app_name,
            version='1.1'
        )

        # Configure Flask app logger
        app.logger.setLevel(logging.INFO)
        app.logger.addHandler(_graylog_handler)

        # Configure root logger to also send to Graylog
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(_graylog_handler)

        # Configure specific loggers for security, application, database
        for logger_name in ['security', 'application', 'database']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.INFO)
            logger.addHandler(_graylog_handler)
            # Prevent duplicate messages
            logger.propagate = False

        # Add console handler for development
        if app.debug:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            app.logger.addHandler(console_handler)

            # Also add console handler to specific loggers
            for logger_name in ['security', 'application', 'database']:
                logger = logging.getLogger(logger_name)
                logger.addHandler(console_handler)

        # Test the connection with explicit extra fields
        app.logger.info("Graylog logging configured successfully", extra={
            'event_type': 'graylog_setup',
            'graylog_host': graylog_host,
            'graylog_port': graylog_port,
            'facility': app_name
        })

        print(f"Graylog logging configured - {graylog_host}:{graylog_port}")

    except Exception as e:
        print(f"Failed to configure Graylog logging: {e}")
        app.logger.error(f"Failed to configure Graylog logging: {e}")
        # Fall back to console logging
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)


def log_security_event(event_type, user_id=None, details=None, request=None):
    """Log security events with standardized format"""
    logger = logging.getLogger("security")

    # Sanitize all user-provided inputs
    safe_event_type = sanitize_log_input(event_type)
    safe_user_id = sanitize_log_input(user_id) if user_id else None
    # Sanitize both keys and values for user-provided details
    safe_details = sanitize_dict(details, sanitize_keys=True) if details else {}

    log_data = {
        "event_type": safe_event_type,
        "timestamp": datetime.now().isoformat(),
        "user_id": safe_user_id,
        "details": safe_details,
        "hostname": socket.gethostname()
    }

    # Build safe request data if request is available
    safe_request_data = {}
    if request:
        # Sanitize request data - be extra careful with request attributes
        try:
            safe_request_data = {
                'ip_address': sanitize_log_input(str(request.remote_addr)) if hasattr(request, 'remote_addr') and request.remote_addr else None,
                'user_agent': sanitize_log_input(str(request.headers.get('User-Agent', ''))) if hasattr(request, 'headers') else None,
                'method': sanitize_log_input(str(request.method)) if hasattr(request, 'method') and request.method else None,
                'path': sanitize_log_input(str(request.path)) if hasattr(request, 'path') and request.path else None,
                'referrer': sanitize_log_input(str(request.referrer)) if hasattr(request, 'referrer') and request.referrer else None
            }
        except Exception:
            # If any exception occurs while accessing request attributes, use safe defaults
            safe_request_data = {'error': 'Failed to parse request data'}
        
        log_data.update({
            "ip_address": safe_request_data.get('ip_address'),
            "user_agent": safe_request_data.get('user_agent'),
            "method": safe_request_data.get('method'),
            "path": safe_request_data.get('path'),
            "referrer": safe_request_data.get('referrer')
        })

    # Create extra dict with only safe, sanitized data
    extra_data = {
        'event_type': safe_event_type,
        'user_id': safe_user_id,
        'details': safe_details
    }
    
    # Only add request_data if we have a request
    if request:
        extra_data['request_data'] = safe_request_data

    # Log with extra fields for Graylog - use parameterized logging
    logger.info("Security event: %s", safe_event_type, extra=extra_data)


def log_application_event(event_type, level="info", details=None, user_id=None):
    """Log application events with standardized format"""
    logger = logging.getLogger("application")

    # Sanitize all user-provided inputs
    safe_event_type = sanitize_log_input(event_type)
    safe_user_id = sanitize_log_input(user_id) if user_id else None
    # Sanitize both keys and values for user-provided details
    safe_details = sanitize_dict(details, sanitize_keys=True) if details else {}

    log_data = {
        "event_type": safe_event_type,
        "timestamp": datetime.now().isoformat(),
        "user_id": safe_user_id,
        "details": safe_details,
        "hostname": socket.gethostname()
    }

    # Validate log level to prevent injection through level parameter
    valid_levels = ['debug', 'info', 'warning', 'error', 'critical']
    safe_level = level.lower() if level and level.lower() in valid_levels else 'info'
    log_method = getattr(logger, safe_level, logger.info)

    # Log with extra fields for Graylog - use parameterized logging
    log_method("Application event: %s", safe_event_type, extra={
        'event_type': safe_event_type,
        'user_id': safe_user_id,
        'details': safe_details
    })


def log_database_event(event_type, table=None, user_id=None, details=None):
    """Log database events with standardized format"""
    logger = logging.getLogger("database")

    # Sanitize all user-provided inputs
    safe_event_type = sanitize_log_input(event_type)
    safe_table = sanitize_log_input(table) if table else None
    safe_user_id = sanitize_log_input(user_id) if user_id else None
    # Sanitize both keys and values for user-provided details
    safe_details = sanitize_dict(details, sanitize_keys=True) if details else {}

    log_data = {
        "event_type": safe_event_type,
        "timestamp": datetime.now().isoformat(),
        "table": safe_table,
        "user_id": safe_user_id,
        "details": safe_details,
        "hostname": socket.gethostname()
    }

    # Log with extra fields for Graylog using parameterized logging
    logger.info("Database event: %s", safe_event_type, extra={
        'event_type': safe_event_type,
        'table': safe_table,
        'user_id': safe_user_id,
        'details': safe_details
    })