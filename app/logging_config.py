import logging
import os
from pygelf import GelfUdpHandler
import socket
from datetime import datetime

# Global variable to store the Graylog handler
_graylog_handler = None


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

        print(f"✅ Graylog logging configured - {graylog_host}:{graylog_port}")

    except Exception as e:
        print(f"❌ Failed to configure Graylog logging: {e}")
        app.logger.error(f"Failed to configure Graylog logging: {e}")
        # Fall back to console logging
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)


def log_security_event(event_type, user_id=None, details=None, request=None):
    """Log security events with standardized format"""
    logger = logging.getLogger("security")

    log_data = {
        "event_type": event_type,
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "details": details or {},
        "hostname": socket.gethostname()
    }

    # Add request information if available
    if request:
        log_data.update({
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get('User-Agent', ''),
            "method": request.method,
            "path": request.path,
            "referrer": request.referrer
        })

    # Log with extra fields for Graylog
    logger.info(f"Security event: {event_type}", extra={
        'event_type': event_type,
        'user_id': user_id,
        'details': details or {},
        'request_data': {
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent', '') if request else None,
            'method': request.method if request else None,
            'path': request.path if request else None,
            'referrer': request.referrer if request else None
        } if request else {}
    })


def log_application_event(event_type, level="info", details=None, user_id=None):
    """Log application events with standardized format"""
    logger = logging.getLogger("application")

    log_data = {
        "event_type": event_type,
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "details": details or {},
        "hostname": socket.gethostname()
    }

    log_method = getattr(logger, level, logger.info)

    # Log with extra fields for Graylog
    log_method(f"Application event: {event_type}", extra={
        'event_type': event_type,
        'user_id': user_id,
        'details': details or {}
    })


def log_database_event(event_type, table=None, user_id=None, details=None):
    """Log database events with standardized format"""
    logger = logging.getLogger("database")

    log_data = {
        "event_type": event_type,
        "timestamp": datetime.now().isoformat(),
        "table": table,
        "user_id": user_id,
        "details": details or {},
        "hostname": socket.gethostname()
    }

    # Log with extra fields for Graylog
    logger.info(f"Database event: {event_type}", extra={
        'event_type': event_type,
        'table': table,
        'user_id': user_id,
        'details': details or {}
    })