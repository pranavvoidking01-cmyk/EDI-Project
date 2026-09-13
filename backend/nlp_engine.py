import os
import re
from dataclasses import dataclass
from functools import lru_cache


ALERT_PREFIX = "[NLP-ALERT]"
PRIORITY_THRESHOLD = 0.7
URGENT_TERMS = re.compile(
    r"\b(urgent|critical|emergency|asap|immediately|blocked|outage|incident|escalate|action required)\b",
    re.IGNORECASE,
)
INFORMATIONAL_TERMS = re.compile(
    r"\b(update|announcement|fyi|information|informational|note|reminder)\b",
    re.IGNORECASE,
)
TEMPORAL_TERMS = re.compile(
    r"\b(deadline|due|by\s+(?:today|tonight|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|before\s+\d|at\s+\d|asap)\b",
    re.IGNORECASE,
)
DATE_TIME_PATTERNS = (
    ("DATE", re.compile(r"\b(?:today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b", re.IGNORECASE)),
    ("TIME", re.compile(r"\b\d{1,2}(?::\d{2})?\s?(?:a\.m\.|p\.m\.|am|pm)\b", re.IGNORECASE)),
    ("DEADLINE", re.compile(r"\b(?:deadline|due|by|before)\b", re.IGNORECASE)),
)


@dataclass(frozen=True)
class NLPAnalysis:
    content: str
    tier: str
    priority_score: float
    temporal_entities: tuple[dict[str, str], ...]
    critical_temporal: bool


@lru_cache(maxsize=1)
def _load_classifier():
    try:
        from transformers import pipeline

        model_name = os.getenv(
            "NLP_PRIORITY_MODEL",
            "distilbert-base-uncased-finetuned-sst-2-english",
        )
        return pipeline("text-classification", model=model_name)
    except Exception:
        return None


@lru_cache(maxsize=1)
def _load_ner():
    try:
        import spacy

        try:
            return spacy.load(os.getenv("SPACY_MODEL", "en_core_web_sm"))
        except (OSError, IOError):
            nlp = spacy.blank("en")
            ruler = nlp.add_pipe("entity_ruler")
            ruler.add_patterns(
                [
                    {"label": "DATE", "pattern": [{"LOWER": value}]} 
                    for value in ("today", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
                ]
                + [
                    {"label": "DEADLINE", "pattern": [{"LOWER": value}]} 
                    for value in ("deadline", "due", "before")
                ]
            )
            return nlp
    except Exception:
        return None


def _extract_temporal_entities(text: str) -> tuple[dict[str, str], ...]:
    entities: list[dict[str, str]] = []
    ner = _load_ner()
    if ner is not None:
        doc = ner(text)
        entities.extend(
            {"label": entity.label_, "text": entity.text}
            for entity in doc.ents
            if entity.label_ in {"DATE", "TIME", "EVENT", "DEADLINE", "ACTION"}
        )

    known = {(entity["label"], entity["text"].lower()) for entity in entities}
    for label, pattern in DATE_TIME_PATTERNS:
        for match in pattern.finditer(text):
            key = (label, match.group(0).lower())
            if key not in known:
                entities.append({"label": label, "text": match.group(0)})
                known.add(key)
    return tuple(entities)


def _model_signal(text: str) -> tuple[str, float]:
    classifier = _load_classifier()
    if classifier is None:
        return "", 0.0
    try:
        result = classifier(text, truncation=True)[0]
        return str(result.get("label", "")).lower(), float(result.get("score", 0.0))
    except Exception:
        return "", 0.0


def analyze_message(text: str) -> NLPAnalysis:
    temporal_entities = _extract_temporal_entities(text)
    critical_temporal = bool(TEMPORAL_TERMS.search(text))
    model_label, model_score = _model_signal(text)

    if URGENT_TERMS.search(text) or critical_temporal:
        tier = "Urgent"
        priority_score = 0.95
    elif INFORMATIONAL_TERMS.search(text) or model_label in {"informational", "positive"}:
        tier = "Informational"
        priority_score = max(0.45, model_score * 0.6)
    else:
        tier = "Routine"
        priority_score = 0.15

    is_alert = tier == "Urgent" or critical_temporal
    content = f"{ALERT_PREFIX} {text}" if is_alert and not text.startswith(ALERT_PREFIX) else text
    return NLPAnalysis(
        content=content,
        tier=tier,
        priority_score=priority_score,
        temporal_entities=temporal_entities,
        critical_temporal=critical_temporal,
    )
