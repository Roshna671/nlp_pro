"""
BiasLens — NLP Engine
Performs sentiment analysis and bias scoring on news articles.
Uses HuggingFace transformers for sentiment and NLTK VADER for keyword extraction.
"""

import numpy as np
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import string
import re
import requests

# Download VADER lexicon if needed
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon", quiet=True)

# Global references
_sentiment_pipeline = None
_vader = None


def query_huggingface_api(text: str):
    """Query the free HuggingFace API instead of running model locally."""
    try:
        API_URL = "https://api-inference.huggingface.co/models/distilbert-base-uncased-finetuned-sst-2-english"
        response = requests.post(API_URL, json={"inputs": text}, timeout=4)
        if response.status_code == 200:
            results = response.json()
            if isinstance(results, list) and len(results) > 0 and isinstance(results[0], list):
                # Format: [[{'label': 'POSITIVE', 'score': 0.99}, ...]]
                return {r["label"]: r["score"] for r in results[0]}
        return None
    except Exception:
        return None


def get_vader():
    """Lazy-load the VADER analyzer."""
    global _vader
    if _vader is None:
        _vader = SentimentIntensityAnalyzer()
    return _vader


def analyze_sentiment(text: str) -> dict:
    """
    Analyze sentiment of a text using both transformers and VADER.
    Returns a dict with positive, negative, neutral, compound scores.
    """
    # Truncate very long texts for the transformer (max 512 tokens)
    truncated = text[:2000]

    # Try HuggingFace API first
    hf_scores = query_huggingface_api(truncated)
    
    # VADER scores
    vader = get_vader()
    vader_scores = vader.polarity_scores(text)

    if hf_scores:
        # Blend: 60% transformer, 40% VADER
        positive = 0.6 * hf_scores.get("POSITIVE", 0) + 0.4 * vader_scores["pos"]
        negative = 0.6 * hf_scores.get("NEGATIVE", 0) + 0.4 * vader_scores["neg"]
    else:
        # Fallback entirely to VADER if free API is rate-limited
        positive = vader_scores["pos"]
        negative = vader_scores["neg"]
    neutral = vader_scores["neu"]  # VADER neutral is more reliable
    compound = vader_scores["compound"]

    return {
        "positive": round(positive, 4),
        "negative": round(negative, 4),
        "neutral": round(neutral, 4),
        "compound": round(compound, 4)
    }


def extract_keywords(text: str) -> dict:
    """
    Extract positive and negative keywords from text using VADER word-level scores.
    Returns dict with 'positive' and 'negative' lists.
    """
    vader = get_vader()
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    seen = set()
    positive_words = []
    negative_words = []

    for word in words:
        if word in seen or len(word) < 3:
            continue
        seen.add(word)
        score = vader.polarity_scores(word)["compound"]
        if score >= 0.3:
            positive_words.append(word)
        elif score <= -0.3:
            negative_words.append(word)

    return {
        "positive": positive_words[:20],  # cap at 20
        "negative": negative_words[:20]
    }


def calculate_bias_score(sentiment: dict) -> tuple:
    """
    Calculate a bias score from sentiment results.
    High polarity (very positive or very negative) = higher bias.
    Returns (score: float, label: str).
    """
    # Bias = how far the sentiment is from neutral
    polarity = abs(sentiment["compound"])
    
    # Also consider the imbalance between positive and negative
    imbalance = abs(sentiment["positive"] - sentiment["negative"])
    
    # Weighted combination
    bias_score = 0.5 * polarity + 0.5 * imbalance
    bias_score = min(bias_score, 1.0)  # clamp
    bias_score = round(bias_score, 4)

    if bias_score < 0.3:
        label = "Neutral"
    elif bias_score < 0.6:
        label = "Leaning"
    else:
        label = "Biased"

    return bias_score, label


def analyze_article(source_name: str, text: str) -> dict:
    """
    Full analysis pipeline for a single article.
    Returns a complete result dict ready for storage.
    """
    sentiment = analyze_sentiment(text)
    bias_score, bias_label = calculate_bias_score(sentiment)
    keywords = extract_keywords(text)

    return {
        "source_name": source_name,
        "article_text": text,
        "sentiment_positive": sentiment["positive"],
        "sentiment_negative": sentiment["negative"],
        "sentiment_neutral": sentiment["neutral"],
        "sentiment_compound": sentiment["compound"],
        "bias_score": bias_score,
        "bias_label": bias_label,
        "positive_keywords": keywords["positive"],
        "negative_keywords": keywords["negative"]
    }
