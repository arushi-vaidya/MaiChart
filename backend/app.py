# backend/app.py - FIXED: Updated import structure
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import os
import logging
import time
from datetime import datetime
from contextlib import asynccontextmanager

# FIXED: Import config correctly
from config import config
from api.routes import api_router
from core.redis_client import RedisClient

# Try to import MongoDB client
try:
    from core.mongodb_client import MongoDBClient, HybridStorageClient
    MONGODB_AVAILABLE = True
except ImportError as e:
    logging.warning(f"MongoDB client not available: {e}")
    MONGODB_AVAILABLE = False
    MongoDBClient = None
    HybridStorageClient = None

# Import medical extraction routes
try:
    from api.medical_routes import medical_router
    MEDICAL_ROUTES_AVAILABLE = True
except ImportError:
    MEDICAL_ROUTES_AVAILABLE = False
    medical_router = None

# Try to import MongoDB-specific routes
try:
    from api.mongodb_routes import mongodb_router
    MONGODB_ROUTES_AVAILABLE = True
except ImportError:
    MONGODB_ROUTES_AVAILABLE = False
    mongodb_router = None


# Async context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown with MongoDB"""
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting FastAPI Medical Transcription System with MongoDB...")
    
    # Get config
    config_name = os.getenv("FASTAPI_ENV", "default")
    config_obj = config[config_name]
    
    # Create necessary directories
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
    
    # Initialize MongoDB client if available and enabled
    mongodb_client = None
    if MONGODB_AVAILABLE and config_obj.ENABLE_MONGODB:
        try:
            mongodb_client = MongoDBClient(
                connection_string=config_obj.MONGODB_CONNECTION_STRING,
                database_name=config_obj.MONGODB_DATABASE_NAME
            )
            app.state.mongodb_client = mongodb_client
            logger.info("✅ MongoDB connection established")
            
            # Create hybrid storage client
            if HybridStorageClient:
                hybrid_client = HybridStorageClient(redis_client, mongodb_client)
                app.state.hybrid_client = hybrid_client
                logger.info("✅ Hybrid storage client initialized")
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            logger.warning("⚠️ Continuing with Redis-only mode")
            config_obj.ENABLE_MONGODB = False
            app.state.mongodb_client = None
            app.state.hybrid_client = None
    else:
        if not MONGODB_AVAILABLE:
            logger.info("📝 MongoDB client not available - using Redis-only mode")
        else:
            logger.info("📝 MongoDB disabled - using Redis-only mode")
        app.state.mongodb_client = None
        app.state.hybrid_client = None
    
    # Initialize medical extraction models if enabled
    enable_medical = os.getenv("ENABLE_MEDICAL_EXTRACTION", "true").lower() == "true"
    if enable_medical and MEDICAL_ROUTES_AVAILABLE:
        try:
            from core.enhanced_medical_extraction_service import enhanced_medical_extractor
            logger.info("🏥 Initializing medical extraction models...")
            await enhanced_medical_extractor.initialize_models()
            app.state.medical_extractor = enhanced_medical_extractor
            logger.info("✅ Medical extraction models loaded")
        except Exception as e:
            logger.warning(f"⚠️ Medical extraction initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down FastAPI Medical Transcription System...")
    if mongodb_client:
        mongodb_client.close_connection()


def create_app(config_name=None):
    """Application factory for FastAPI with MongoDB support"""
    
    if config_name is None:
        config_name = os.environ.get("FASTAPI_ENV", "default")

    config_obj = config[config_name]
    
    # Create FastAPI app with lifespan
    app = FastAPI(
        title="MaiChart - Medical Voice Notes API with MongoDB",
        description="AI-powered medical voice note transcription with persistent MongoDB storage",
        version="2.2.0",
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
        if hasattr(app, 'logger'):
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
    
    # Include MongoDB routes if available
    if MONGODB_ROUTES_AVAILABLE and mongodb_router:
        app.include_router(mongodb_router, prefix="/api", tags=["mongodb"])
        logging.info("✅ MongoDB-specific routes enabled")
    
    # Enhanced health check endpoint
    @app.get("/health")
    async def health_check():
        """Root health check endpoint with storage status"""
        mongodb_status = "disabled"
        if config_obj.ENABLE_MONGODB and MONGODB_AVAILABLE:
            if hasattr(app.state, 'mongodb_client') and app.state.mongodb_client:
                mongodb_healthy = app.state.mongodb_client.health_check()
                mongodb_status = "healthy" if mongodb_healthy else "unhealthy"
            else:
                mongodb_status = "connection_failed"
        elif not MONGODB_AVAILABLE:
            mongodb_status = "not_installed"
        
        storage_strategy = config_obj.STORAGE_STRATEGY if config_obj.ENABLE_MONGODB else "redis_only"
        
        return {
            "status": "healthy",
            "service": "MaiChart Medical Transcription API",
            "version": "2.2.0",
            "timestamp": datetime.utcnow().isoformat(),
            "storage": {
                "strategy": storage_strategy,
                "redis": "enabled",
                "mongodb": mongodb_status,
                "mongodb_available": MONGODB_AVAILABLE,
                "analytics_enabled": config_obj.ENABLE_MEDICAL_ANALYTICS and config_obj.ENABLE_MONGODB
            },
            "features": {
                "transcription": "enabled",
                "medical_extraction": "enabled" if os.getenv("ENABLE_MEDICAL_EXTRACTION", "true").lower() == "true" else "disabled",
                "parallel_chunking": "enabled",
                "persistent_storage": mongodb_status not in ["disabled", "not_installed"]
            }
        }
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with MongoDB features"""
        storage_info = "Redis + MongoDB hybrid storage" if config_obj.ENABLE_MONGODB and MONGODB_AVAILABLE else "Redis-only storage"
        
        return {
            "message": "MaiChart Medical Voice Notes API with MongoDB",
            "version": "2.2.0",
            "storage": storage_info,
            "features": [
                "🎤 Audio transcription with AssemblyAI",
                "🏥 Medical information extraction with OpenAI GPT-4",
                "⚡ Parallel chunk processing for large files",
                "📊 Structured FHIR-like medical data output",
                "🚨 Medical alerts and critical information detection",
                "💾 Persistent MongoDB storage for analytics" if config_obj.ENABLE_MONGODB and MONGODB_AVAILABLE else None,
                "🔍 Advanced medical data querying and search" if config_obj.ENABLE_MONGODB and MONGODB_AVAILABLE else None
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
                "medical_analytics": "/api/medical_analytics" if config_obj.ENABLE_MONGODB and MONGODB_AVAILABLE else None,
                "patient_search": "/api/patients/search" if config_obj.ENABLE_MONGODB and MONGODB_AVAILABLE else None
            }
        }
    
    return app


def setup_middleware(app: FastAPI, config_obj):
    """Setup FastAPI middleware"""
    
    # CORS middleware
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
            allowed_hosts=["*"]
        )


def setup_logging(app: FastAPI, config_obj):
    """Setup application logging"""
    
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
    
    logger.info("🚀 FastAPI Medical Transcription System with MongoDB startup")


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration
    config_name = os.getenv("FASTAPI_ENV", "default")
    config_obj = config[config_name]
    
    print("🚀 Starting Enhanced FastAPI Medical Transcription System with MongoDB...")
    print(f"📁 Upload folder: {config_obj.UPLOAD_FOLDER}")
    print(f"📄 Transcripts folder: {config_obj.TRANSCRIPTS_FOLDER}")
    print(f"🔧 Environment: {config_name}")
    print(f"💾 MongoDB: {'Enabled' if config_obj.ENABLE_MONGODB and MONGODB_AVAILABLE else 'Disabled'}")
    print(f"🏥 Medical extraction: {'Enabled' if os.getenv('ENABLE_MEDICAL_EXTRACTION', 'true').lower() == 'true' else 'Disabled'}")
    print(f"🌐 Server will be available at: http://{config_obj.HOST}:{config_obj.PORT}")
    
    # Run with uvicorn
    uvicorn.run(
        "app:app",
        host=config_obj.HOST,
        port=config_obj.PORT,
        reload=config_obj.DEBUG,
        log_level="info"
    )