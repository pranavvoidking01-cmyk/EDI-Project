import re
from collections import Counter

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy import text
from sqlalchemy.orm import Session

ALERT_PREFIX_PATTERN = re.compile(r"\[NLP-ALERT\]\s*", re.IGNORECASE)
TOKEN_PATTERN = re.compile(r"(?u)\b[a-zA-Z][a-zA-Z0-9_-]{2,}\b")
CUSTOM_STOP_WORDS = {"nlp", "alert", "message", "messages", "fyi"}


def fetch_message_content(db: Session) -> list[str]:
    contents = db.execute(text("SELECT content FROM messages ORDER BY timestamp ASC")).scalars().all()
    return [ALERT_PREFIX_PATTERN.sub("", content).strip() for content in contents if content.strip()]


def recommend_priority_keywords(db: Session, limit: int = 5) -> list[str]:
    documents = fetch_message_content(db)
    if not documents:
        return []

    vectorizer = TfidfVectorizer(
        stop_words="english",
        token_pattern=TOKEN_PATTERN.pattern,
        max_features=200,
    )
    try:
        matrix = vectorizer.fit_transform(documents)
    except ValueError:
        return []

    terms = vectorizer.get_feature_names_out()
    tfidf_scores = matrix.sum(axis=0).A1
    frequencies = Counter(
        token.lower()
        for document in documents
        for token in TOKEN_PATTERN.findall(document)
        if token.lower() not in CUSTOM_STOP_WORDS
    )
    max_frequency = max(frequencies.values(), default=1)
    combined_scores = {
        term: float(tfidf_scores[index]) + (frequencies[term] / max_frequency)
        for index, term in enumerate(terms)
    }

    if len(documents) > 1 and matrix.shape[1] > 1:
        cluster_count = min(3, len(documents), matrix.shape[1])
        clusters = KMeans(n_clusters=cluster_count, random_state=42, n_init=10).fit(matrix)
        for cluster in range(cluster_count):
            cluster_center = clusters.cluster_centers_[cluster]
            representative_indexes = cluster_center.argsort()[-3:]
            for index in representative_indexes:
                combined_scores[terms[index]] += 0.2

    return [
        term
        for term, _ in sorted(combined_scores.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]
