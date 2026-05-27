"""
AI Aura & Personality Reader - FastAPI Backend
================================================

Main API service that orchestrates the aura analysis pipeline:
- Receives text input via POST /analyze
- Produces events to Kafka for async processing
- Stores and serves analysis results
- Provides health check and results endpoints

Author: Project AURA Team
"""

import os
import json
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from producer import AuraProducer
from ai_service import analyze_personality, analyze_mbti

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("aura.api")

# ─────────────────────────────────────────────
# In-Memory Results Store
# ─────────────────────────────────────────────
results_store: dict[str, dict] = {}
results_lock = asyncio.Lock()

# ─────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    """Request body for the /analyze endpoint."""
    text: str = Field(
        ...,
        min_length=3,
        max_length=5000,
        description="Text input to analyze for aura/personality reading",
        examples=["I love building futuristic systems and having deep conversations."],
    )
    user_id: str = Field(
        default="anonymous",
        description="Optional user identifier",
    )


class AnalyzeResponse(BaseModel):
    """Response from the /analyze endpoint."""
    request_id: str
    status: str
    message: str


class AuraResult(BaseModel):
    """Full aura analysis result."""
    request_id: str
    user_id: str
    aura_type: str
    aura_color: str
    energy_level: str
    personality_traits: list[str]
    energy_score: int
    confidence_score: int
    sentiment: dict
    keywords_detected: list[str]
    timestamp: str


class StoreResultRequest(BaseModel):
    """Internal request to store a processed result."""
    request_id: str
    user_id: str = "anonymous"
    aura_type: str
    aura_color: str
    energy_level: str
    personality_traits: list[str]
    energy_score: int
    confidence_score: int
    sentiment: dict
    keywords_detected: list[str]
    timestamp: str


# ─────────────────────────────────────────────
# Application Lifespan
# ─────────────────────────────────────────────
producer: Optional[AuraProducer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    global producer

    # Ensure static directories exist
    os.makedirs("static/uploads", exist_ok=True)

    logger.info("🚀 Starting AI Aura & Personality Reader API...")
    logger.info(f"📡 Kafka Bootstrap: {KAFKA_BOOTSTRAP}")

    # Initialize Kafka producer with retry
    max_retries = 15
    for attempt in range(1, max_retries + 1):
        try:
            producer = AuraProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
            logger.info("✅ Kafka Producer connected successfully")
            break
        except Exception as e:
            logger.warning(f"⏳ Kafka not ready (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                await asyncio.sleep(3)
            else:
                logger.error("❌ Could not connect to Kafka after retries. Starting without Kafka.")
                producer = None

    logger.info("🌟 API is ready to receive requests!")

    yield

    # Shutdown
    logger.info("🛑 Shutting down API...")
    if producer:
        producer.close()
        logger.info("✅ Kafka Producer closed")


# ─────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────
app = FastAPI(
    title="🔮 AI Aura & Personality Reader",
    description=(
        "Real-time AI-powered distributed system that analyzes user text input "
        "and generates aura/personality interpretations using Kafka event streaming, "
        "FastAPI, and NLP processing."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - allow Streamlit dashboard to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder to serve selfie uploads
app.mount("/static", StaticFiles(directory="static"), name="static")


# ─────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """Health check and welcome endpoint."""
    return {
        "service": "AI Aura & Personality Reader",
        "status": "online",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "POST /analyze",
            "results": "GET /results",
            "result_by_id": "GET /results/{request_id}",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_text(request: AnalyzeRequest):
    """
    Submit text for aura/personality analysis.

    The text is sent to Kafka for asynchronous processing by the consumer service.
    If Kafka is unavailable, falls back to synchronous processing.

    Returns a request_id that can be used to retrieve results via GET /results/{request_id}.
    """
    logger.info(f"📨 Received analysis request from user: {request.user_id}")
    logger.info(f"📝 Text preview: {request.text[:80]}...")

    request_id = str(uuid.uuid4())

    # Try Kafka-based async processing first
    if producer:
        try:
            request_id = producer.send_event(
                text=request.text,
                user_id=request.user_id,
            )
            logger.info(f"✅ Event produced to Kafka | request_id={request_id}")

            return AnalyzeResponse(
                request_id=request_id,
                status="processing",
                message="Your aura is being analyzed! Results will appear shortly.",
            )
        except Exception as e:
            logger.error(f"❌ Kafka produce failed: {e}. Falling back to sync processing.")

    # Fallback: synchronous processing (no Kafka)
    logger.info("⚡ Using synchronous processing (Kafka unavailable)")
    result = analyze_personality(request.text)
    result["request_id"] = request_id
    result["user_id"] = request.user_id

    async with results_lock:
        results_store[request_id] = result

    logger.info(f"✅ Sync analysis complete | aura={result['aura_type']} | request_id={request_id}")

    return AnalyzeResponse(
        request_id=request_id,
        status="completed",
        message=f"Your aura has been revealed: {result['aura_type']}!",
    )


@app.post("/analyze/mbti", tags=["MBTI"])
async def analyze_mbti_personality(
    answers: str = Form(..., description="JSON stringified question answers dict"),
    file: Optional[UploadFile] = File(None)
):
    """
    Analyze MBTI questionnaire responses and optional camera photo capture.

    Processes the photo to extract a visual aura and dynamic vibe shifts.
    Stores the photo under static/uploads/ and returns the full MBTI profile.
    """
    logger.info("📨 Received MBTI analysis request")

    try:
        answers_dict = json.loads(answers)
    except Exception as e:
        logger.error(f"Failed to parse answers JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON format for answers.")

    image_bytes = None
    if file:
        try:
            image_bytes = await file.read()
        except Exception as e:
            logger.error(f"Failed to read file bytes: {e}")

    # Run the integration analysis
    result = analyze_mbti(answers_dict, image_bytes)

    # Store result locally
    request_id = result.get("request_id") or str(uuid.uuid4())
    result["request_id"] = request_id
    result["user_id"] = "anonymous"

    # Save the photo to disk
    if file and image_bytes:
        try:
            file_path = f"static/uploads/{request_id}.jpg"
            with open(file_path, "wb") as f:
                f.write(image_bytes)
            # The URL to reference from the Streamlit UI
            result["photo_url"] = f"/static/uploads/{request_id}.jpg"
            logger.info(f"💾 Selfie saved for request_id={request_id}")
        except Exception as e:
            logger.error(f"Failed to save selfie photo: {e}")
            result["photo_url"] = None
    else:
        result["photo_url"] = None

    async with results_lock:
        results_store[request_id] = result

    logger.info(f"✅ MBTI analysis complete | type={result['mbti_type']} | request_id={request_id}")
    return result


@app.get("/results", response_model=list[AuraResult], tags=["Results"])
async def get_all_results():
    """
    Retrieve all analysis results.

    Returns the most recent results first (up to 50).
    """
    async with results_lock:
        all_results = list(results_store.values())

    # Sort by timestamp descending (most recent first)
    all_results.sort(key=lambda r: r.get("timestamp", ""), reverse=True)

    return all_results[:50]


@app.get("/results/{request_id}", tags=["Results"])
async def get_result(request_id: str):
    """
    Retrieve a specific analysis result by request ID.

    Returns 404 if the result is not yet available (still processing)
    or if the request_id is unknown.
    """
    async with results_lock:
        result = results_store.get(request_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Result not found. It may still be processing.",
                "request_id": request_id,
                "status": "pending",
            },
        )

    return result


@app.post("/internal/store_result", tags=["Internal"])
async def store_result(result: StoreResultRequest):
    """
    Internal endpoint used by the Kafka consumer to store processed results.

    This endpoint is not intended for external use.
    """
    result_data = result.model_dump()

    async with results_lock:
        results_store[result.request_id] = result_data

    logger.info(
        f"💾 Result stored | request_id={result.request_id} | "
        f"aura={result.aura_type} | confidence={result.confidence_score}%"
    )

    return {"status": "stored", "request_id": result.request_id}


# ─────────────────────────────────────────────
# Error Handlers
# ─────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"❌ Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# ─────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
