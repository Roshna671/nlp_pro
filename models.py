"""
BiasLens — Pydantic Models
Request/Response schemas for the FastAPI endpoints.
"""

from pydantic import BaseModel
from typing import List, Optional


class ArticleInput(BaseModel):
    """Single article input for analysis."""
    source_name: str
    text: str


class AnalysisRequest(BaseModel):
    """Request to analyze multiple articles on a topic."""
    topic: str
    articles: List[ArticleInput]


class ArticleResult(BaseModel):
    """Result of analyzing a single article."""
    source_name: str
    article_text: str
    sentiment_positive: float
    sentiment_negative: float
    sentiment_neutral: float
    sentiment_compound: float
    bias_score: float
    bias_label: str
    positive_keywords: List[str]
    negative_keywords: List[str]


class AnalysisResponse(BaseModel):
    """Full analysis response."""
    id: int
    topic: str
    created_at: str
    total_sources: int
    avg_bias: float
    bias_spread: float
    articles: List[ArticleResult]


class AnalysisSummary(BaseModel):
    """Summary of an analysis (no article text)."""
    id: int
    topic: str
    created_at: str
    total_sources: int
    avg_bias: float
    bias_spread: float


class StatsResponse(BaseModel):
    """Aggregate statistics."""
    total_analyses: int
    total_articles: int
    average_bias: float
    neutral_count: int
    biased_count: int
