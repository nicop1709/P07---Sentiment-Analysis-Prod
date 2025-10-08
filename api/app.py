import os, time, logging
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import re
import spacy
nlp = spacy.load("en_core_web_sm")
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from sklearn.feature_extraction.text import CountVectorizer,TfidfVectorizer
import tensorflow_hub as hub
from nltk.stem import SnowballStemmer
_STEMMER_EN = SnowballStemmer("english")

from dotenv import load_dotenv
load_dotenv()
# --- App Insights via OpenTelemetry (recommandé) ---
from azure.monitor.opentelemetry import configure_azure_monitor

stopwords = [
    "i","me","my","myself","we","our","ours","ourselves",
    "you","your","yours","yourself","yourselves",
    "he","him","his","himself",
    "she","her","hers","herself",
    "it","its","itself",
    "they","them","their","theirs","themselves",
    "what","which","who","whom",
    "this","that","these","those",
    "am","is","are","was","were","be","been","being",
    "have","has","had","having",
    "do","does","did","doing",
    "a","an","the","and","but","if","or","because","as","until","while",
    "of","at","by","for","with","about","against","between","into","through",
    "during","before","after","above","below",
    "to","from","up","down","in","out","on","off","over","under",
    "again","further","then","once","here","there","when","where","why","how",
    "all","any","both","each","few","more","most","other","some","such",
    "no","nor","not","only","own","same","so","than","too","very",
    "s","t","can","will","just","don","should","now"
]
STOPWORDS_SET = set(stopwords)


# --- Chargement modèle TensorFlow (optionnel si non dispo) ---
TF_AVAILABLE = True

import numpy as np
import tensorflow as tf


# -------- Config ----------
APPINSIGHTS_CONN = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
if not APPINSIGHTS_CONN:
    raise RuntimeError("APPLICATIONINSIGHTS_CONNECTION_STRING manquante (dotenv/.env).")

configure_azure_monitor(connection_string=APPINSIGHTS_CONN)

MODEL_DIR = os.getenv("MODEL_DIR", "./models/savedmodel")
MODEL_VERSION = os.getenv("MODEL_VERSION", "dev")

# Logger standard (capté par OpenTelemetry)
logger = logging.getLogger("p07_sentiment_api")
logger.setLevel(logging.INFO)

# -------- FastAPI ----------
app = FastAPI(title="P07 Sentiment API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# -------- Modèle ----------
model = None
if TF_AVAILABLE and os.path.isdir(MODEL_DIR):
    try:
        model = tf.keras.models.load_model(MODEL_DIR)
        logger.info(f"Model loaded from {MODEL_DIR}", extra={"custom_dimensions":{"model_version": MODEL_VERSION}})
    except Exception as e:
        logger.exception("Failed to load TF model, fallback to mock.", extra={"custom_dimensions":{"err": str(e)}})

def preprocess_text_function(text,mode="lemma"):
    """
    Clean + normalize English text, then apply either lemmatization or stemming.

    Parameters
    ----------
    text : str
        Raw input text.
    mode : {"lemma", "stem"}
        - "lemma" (default): spaCy lemmatization
        - "stem" : NLTK Snowball stemming

    Returns
    -------
    str
        Preprocessed string (tokens space-joined).
    """
    if mode not in {"lemma", "stem"}:
        raise ValueError("mode must be 'lemma' or 'stem'")

    # 1) Nettoyage basique + lowercase
    text = re.sub(r"[^a-zA-Z ]+", " ", str(text)).lower().strip()

    # 2) Tokenisation (spaCy)
    doc = nlp(text)

    # 3) Filtrage & normalisation
    out_tokens = []
    for tok in doc:
        t = tok.text

        # ignore stopwords et tokens trop courts (sur le token original)
        if t in ENGLISH_STOP_WORDS or len(t) <= 2:
            continue

        if mode == "lemma":
            norm = tok.lemma_
        else:  # mode == "stem"
            norm = _STEMMER_EN.stem(t)

        # re-filtre les très courts après normalisation (ex: stems trop courts)
        if len(norm) > 2:
            out_tokens.append(norm)

    return " ".join(out_tokens)

def predict_proba_positive(text: str) -> float:
    """
    Renvoie une proba de 'positive'.
    - Si modèle TF dispo: utilise model.predict
    - Sinon: mock rapide basé sur mots-clés (pour test pipeline).
    """
    if model is not None and TF_AVAILABLE:
        x = preprocess_text_function(text)
        p = float(model.predict(x, verbose=0).ravel()[0])
        return max(0.0, min(1.0, p))
    # --- fallback mock ---
    txt = text.lower()
    good = sum(w in txt for w in ["good","great","love","amazing","excellent","super","cool","merci","génial"])
    bad  = sum(w in txt for w in ["bad","hate","awful","terrible","horrible","nul","pourri","triste"])
    score = 0.5 + 0.1*(good - bad)
    return max(0.0, min(1.0, score))

# -------- Schemas ----------
class PredictIn(BaseModel):
    text: str

class PredictOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    sentiment: Literal["positive","negative"]
    score: float
    model_version: str
    latency_ms: float

class FeedbackIn(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    text: str
    predicted: Literal["positive","negative"]
    score: float
    is_valid: bool
    model_version: Optional[str] = None

# -------- Endpoints ----------
@app.post("/predict", response_model=PredictOut)
def predict(payload: PredictIn):
    t0 = time.time()
    score = predict_proba_positive(payload.text)
    sentiment = "positive" if score >= 0.5 else "negative"
    latency_ms = (time.time() - t0) * 1000.0

    # Trace prediction
    logger.info(
        "prediction",
        extra={"custom_dimensions":{
            "score": score,
            "sentiment": sentiment,
            "model_version": MODEL_VERSION,
            "latency_ms": latency_ms
        }}
    )

    return PredictOut(
        sentiment=sentiment,
        score=score,
        model_version=MODEL_VERSION,
        latency_ms=latency_ms
    )

@app.post("/feedback")
def feedback(payload: FeedbackIn):
    # Trace feedback utilisateur (WARNING si non-validation pour les alertes)
    msg = "user_feedback"
    level = logging.WARNING if (payload.is_valid is False) else logging.INFO
    logger.log(
        level,
        msg,
        extra={"custom_dimensions":{
            "is_valid": payload.is_valid,
            "predicted": payload.predicted,
            "score": payload.score,
            "model_version": payload.model_version or MODEL_VERSION
        }}
    )
    return {"ok": True}
