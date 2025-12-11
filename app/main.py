"""
Main FastAPI application for the workflow engine.

This is the entry point that initializes the app, storage, and routes.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.api.routes import router, set_storage
from app.storage.sqlite_storage import SQLiteStorage
from app.workflows.code_review import register_code_review_tools  # NEW IMPORT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Storage instance
storage: SQLiteStorage = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    
    Handles initialization and cleanup of resources.
    """
    # Startup
    global storage
    logger.info("Starting workflow engine...")
    
    # Initialize storage
    storage = SQLiteStorage("data/workflow.db")
    await storage.initialize()
    set_storage(storage)
    
    logger.info("✅ Storage initialized")
    
    # Register workflow tools
    register_code_review_tools()  # NEW LINE
    logger.info("✅ Workflow tools registered")
    
    logger.info("✅ Workflow engine ready!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down workflow engine...")
    await storage.close()
    logger.info("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Workflow Engine API",
    description="A minimal workflow/graph engine for executing agent workflows",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware (for frontend integration if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)


@app.get("/", tags=["health"])
async def root():
    """
    Root endpoint - health check.
    
    Returns basic API information.
    """
    return {
        "message": "Workflow Engine API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the operational status of the API.
    """
    return {
        "status": "healthy",
        "storage": "connected" if storage else "disconnected"
    }