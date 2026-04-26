"""
BiasLens — FastAPI Backend
Serves the REST API and the static frontend.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os

import database
import nlp_engine
from models import AnalysisRequest, AnalysisResponse, AnalysisSummary, StatsResponse

# Initialize database on startup
database.init_db()

app = FastAPI(title="BiasLens API", version="1.0.0")

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_articles(request: AnalysisRequest):
    """Analyze multiple articles for sentiment and bias."""
    if not request.articles:
        raise HTTPException(status_code=400, detail="At least one article is required")
    if not request.topic.strip():
        raise HTTPException(status_code=400, detail="Topic is required")

    results = []
    for article in request.articles:
        result = nlp_engine.analyze_article(article.source_name, article.text)
        results.append(result)

    analysis_id = database.save_analysis(request.topic.strip(), results)
    analysis = database.get_analysis_by_id(analysis_id)
    return analysis


@app.get("/api/history", response_model=List[AnalysisSummary])
async def get_history():
    """Get all past analyses."""
    return database.get_all_analyses()


@app.get("/api/history/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: int):
    """Get a specific analysis with full details."""
    analysis = database.get_analysis_by_id(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@app.delete("/api/history/{analysis_id}")
async def delete_analysis(analysis_id: int):
    """Delete an analysis."""
    deleted = database.delete_analysis(analysis_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"message": "Analysis deleted", "id": analysis_id}


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get aggregate statistics."""
    return database.get_stats()


STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
