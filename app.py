from flask import Flask, request, g
from flask_cors import CORS
import os
import logging
from datetime import datetime
import time

from config import config
from api.routes import api_bp
from core.redis_client import RedisClient


def create_app(config_name=None):
    """Application factory"""

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    app.config["SESSION_COOKIE_SECURE"] = False  
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # Enable CORS
    CORS(app)

    # Create necessary directories
    config[config_name].create_directories()

    # Setup logging
    setup_logging(app)

    # Add request timing middleware
    @app.before_request
    def before_request():
        g.start_time = time.time()

    @app.after_request
    def log_request(response):
        """Log request details"""
        try:
            duration = time.time() - g.get('start_time', 0)
            app.logger.info(
                f"📡 {request.method} {request.path} - {response.status_code} "
                f"({duration:.3f}s)"
            )
        except Exception as e:
            app.logger.error(f"Error logging request: {e}")
        return response

    # Register blueprints
    app.register_blueprint(api_bp)

    # Initialize Redis client (test connection) - Updated to pass all credentials
    try:
        redis_client = RedisClient(
            host=app.config["REDIS_HOST"],
            port=app.config["REDIS_PORT"],
            password=app.config["REDIS_PASSWORD"],  
            db=app.config["REDIS_DB"],
        )
        app.logger.info("Redis connection established")
    except Exception as e:
        app.logger.error(f"Redis connection failed: {e}")
        raise

    return app


def setup_logging(app):
    """Setup application logging"""

    if not app.debug:
        # Production logging
        log_dir = app.config["LOGS_FOLDER"]
        log_file = log_dir / "app.log"

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
            )
        )

        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info("Audio Processing System startup")

    # Console logging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    app.logger.addHandler(console_handler)


if __name__ == "__main__":
    app = create_app()

    app.logger.info("Starting Flask application...")
    app.logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    app.logger.info(f"Transcripts folder: {app.config['TRANSCRIPTS_FOLDER']}")

    # Check for SSL certificates
    from pathlib import Path

    cert_file = Path("ssl/cert.pem")
    key_file = Path("ssl/key.pem")

    if cert_file.exists() and key_file.exists():
        app.logger.info("SSL certificates found - starting HTTPS server")
        app.logger.info("Application ready at: https://localhost:5001")
        app.logger.info(
            "⚠️  Browser will show security warning - click 'Advanced' → 'Proceed to localhost'"
        )

        # Run with SSL
        app.run(
            debug=app.config["DEBUG"],
            host=app.config["HOST"],
            port=app.config["PORT"],
            ssl_context=(str(cert_file), str(key_file)),
            use_reloader=False,
        )
    else:
        app.logger.info("No SSL certificates found - starting HTTP server")
        app.logger.info("Application ready at: http://localhost:5001")
        app.logger.warning(
            "⚠️  Microphone recording requires HTTPS. Run 'python generate_ssl_cert.py' to enable HTTPS"
        )

        # Run without SSL
        app.run(
            debug=app.config["DEBUG"],
            host=app.config["HOST"],
            port=app.config["PORT"],
            use_reloader=False,
        )