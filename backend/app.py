from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import os
import logging
import time
from datetime import datetime
from contextlib import asynccontextmanager

from config import config
from api.routes import api_router
from core.redis_client import RedisClient

# Import medical extraction routes
try:
    from api.medical_routes import medical_router
    MEDICAL_ROUTES_AVAILABLE = True
except ImportError:
    MEDICAL_ROUTES_AVAILABLE = False
    medical_router = None


# Async context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    # Startup
    logger = getattr(app, "logger", logging.getLogger(__name__))
    logger.info("Starting FastAPI Medical Transcription System with Enhanced Medical Extraction...")
    
    # Create necessary directories
    config_obj = config[os.getenv("FASTAPI_ENV", "default")]
    config_obj.create_directories()
    
    # Initialize Redis client
    try:
        redis_client = RedisClient(
            host=config_obj.REDIS_HOST,
            port=config_obj.REDIS_PORT,
            password=config_obj.REDIS_PASSWORD,
            db=config_obj.REDIS_DB,
        )
        app.state.redis_client = redis_client
        logger.info("✅ Redis connection established")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        raise
    
    # Initialize medical extraction models if enabled
    enable_medical = os.getenv("ENABLE_MEDICAL_EXTRACTION", "true").lower() == "true"
    if enable_medical and MEDICAL_ROUTES_AVAILABLE:
        try:
            from core.enhanced_medical_extraction_service import enhanced_medical_extractor
            logger.info("🏥 Initializing medical extraction models...")
            await enhanced_medical_extractor.initialize_models()
            app.state.medical_extractor = enhanced_medical_extractor
            logger.info("✅ Medical extraction models loaded (OpenAI GPT-4 only)")
        except Exception as e:
            logger.warning(f"⚠️ Medical extraction initialization failed: {e}")
            logger.warning("Medical extraction features will be disabled")
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI Medical Transcription System...")


def create_app(config_name=None):
    """Application factory for FastAPI with medical extraction"""
    
    if config_name is None:
        config_name = os.environ.get("FASTAPI_ENV", "default")

    config_obj = config[config_name]
    
    # Create FastAPI app with lifespan
    app = FastAPI(
        title="MaiChart - Enhanced Medical Voice Notes API",
        description="AI-powered medical voice note transcription with structured data extraction using OpenAI GPT-4",
        version="2.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Store config in app state
    app.state.config = config_obj
    
    # Setup logging
    setup_logging(app, config_obj)
    
    # Add middleware
    setup_middleware(app, config_obj)
    
    # Add request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log request
        app.logger.info( 
            f"📡 {request.method} {request.url.path} - {response.status_code} "
            f"({process_time:.3f}s)"
        )
        
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # Include API routes
    app.include_router(api_router, prefix="/api")
    
    # Include medical routes if available
    if MEDICAL_ROUTES_AVAILABLE and medical_router:
        app.include_router(medical_router, prefix="/api", tags=["medical"])
        logging.info("✅ Medical extraction routes enabled")
    else:
        logging.warning("⚠️ Medical extraction routes not available")
    
    # Enhanced health check endpoint
    @app.get("/health")
    async def health_check():
        """Root health check endpoint with medical extraction status"""
        medical_status = "disabled"
        if MEDICAL_ROUTES_AVAILABLE:
            medical_status = "enabled" if os.getenv("ENABLE_MEDICAL_EXTRACTION", "true").lower() == "true" else "configured_but_disabled"
        
        return {
            "status": "healthy",
            "service": "MaiChart Medical Transcription API",
            "version": "2.1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "features": {
                "transcription": "enabled",
                "medical_extraction": medical_status,
                "parallel_chunking": "enabled",
                "openai_gpt4": medical_status if os.getenv("OPENAI_API_KEY") else "no_api_key"
            }
        }
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with feature overview"""
        return {
            "message": "MaiChart Enhanced Medical Voice Notes API",
            "version": "2.1.0",
            "features": [
                "🎤 Audio transcription with AssemblyAI",
                "🏥 Medical information extraction with OpenAI GPT-4",
                "⚡ Parallel chunk processing for large files",
                "📊 Structured FHIR-like medical data output",
                "🚨 Medical alerts and critical information detection"
            ],
            "endpoints": {
                "docs": "/docs",
                "health": "/health",
                "transcription_api": "/api",
                "medical_data_api": "/api/medical_data",
                "upload": "/api/upload_audio",
                "status": "/api/status/{session_id}",
                "transcript": "/api/transcript/{session_id}",
                "medical_data": "/api/medical_data/{session_id}",
                "medical_summary": "/api/medical_summary/{session_id}",
                "medical_alerts": "/api/medical_alerts/{session_id}"
            }
        }
    
    return app


def setup_middleware(app: FastAPI, config_obj):
    """Setup FastAPI middleware"""
    
    # CORS middleware with medical API support
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Trusted host middleware (for production)
    if not config_obj.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware, 
            allowed_hosts=["*"]  # Configure this properly in production
        )


def setup_logging(app: FastAPI, config_obj):
    """Setup application logging"""
    
    # Create logger
    logger = logging.getLogger(__name__)
    app.logger = logger 
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler for production
    if not config_obj.DEBUG:
        log_dir = config_obj.LOGS_FOLDER
        log_file = log_dir / "app.log"
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)
    
    if not config_obj.DEBUG:
        logger.info("🚀 FastAPI Medical Transcription System with Medical Extraction startup")


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration
    config_name = os.getenv("FASTAPI_ENV", "default")
    config_obj = config[config_name]
    
    print("🚀 Starting Enhanced FastAPI Medical Transcription System...")
    print(f"📁 Upload folder: {config_obj.UPLOAD_FOLDER}")
    print(f"📄 Transcripts folder: {config_obj.TRANSCRIPTS_FOLDER}")
    print(f"🔧 Environment: {config_name}")
    print(f"🏥 Medical extraction: {'Enabled' if os.getenv('ENABLE_MEDICAL_EXTRACTION', 'true').lower() == 'true' else 'Disabled'}")
    print(f"🤖 OpenAI API: {'Configured' if os.getenv('OPENAI_API_KEY') else 'Not configured'}")
    print(f"🌐 Server will be available at: http://{config_obj.HOST}:{config_obj.PORT}")
    
    # Run with uvicorn
    uvicorn.run(
        "app:app",
        host=config_obj.HOST,
        port=config_obj.PORT,
        reload=config_obj.DEBUG,
        log_level="info"
    )