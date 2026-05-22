"""
Raggruppa articoli sullo stesso evento usando TF-IDF + cosine similarity.
Nessun modello da scaricare, gira in-process, zero costi.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from ..models.news import Article

SIMILARITY_THRESHOLD = 0.25  # articoli con score >= soglia → stesso evento


def _text(article: Article) -> str:
    return f"{article.title} {article.snippet or ''}"


def cluster_articles(articles: list[Article]) -> list[list[Article]]:
    if not articles:
        return []

    texts = [_text(a) for a in articles]
    try:
        vectorizer = TfidfVectorizer(stop_words=None, max_features=5000)
        matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return [[a] for a in articles]

    sim = cosine_similarity(matrix)
    n = len(articles)
    visited = [False] * n
    clusters: list[list[Article]] = []

    for i in range(n):
        if visited[i]:
            continue
        cluster = [articles[i]]
        visited[i] = True
        for j in range(i + 1, n):
            if not visited[j] and sim[i, j] >= SIMILARITY_THRESHOLD:
                cluster.append(articles[j])
                visited[j] = True
        clusters.append(cluster)

    # Ordina per dimensione cluster (più fonti = più rilevante)
    clusters.sort(key=len, reverse=True)
    return clusters
