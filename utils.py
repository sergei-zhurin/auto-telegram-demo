import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer

from config import STORAGE_PATH, logger, MODELS_PATH


def compute_centroids(examples_file, centroids_file):
    # Загружаем размеченные новости
    with open(examples_file, 'r', encoding='utf-8') as f:
        examples_list = json.load(f)

    # Загружаем модель
    model = SentenceTransformer(os.path.join(MODELS_PATH, 'all-MiniLM-L6-v2'), device='cpu')

    # Группируем новости по категориям
    category_embeddings = {}
    for news in examples_list:
        category = news['category']
        text = f"{news['header']}. {news['summary']}"
        embedding = model.encode(text, normalize_embeddings=True)

        # Если категории нет - создаём
        if category not in category_embeddings:
            category_embeddings[category] = []
        category_embeddings[category].append(embedding)

    # Вычисляем центроид для каждой категории
    centroids = {}
    for category, embeddings in category_embeddings.items():
        embeddings_matrix = np.vstack(embeddings)
        centroid = np.mean(embeddings_matrix, axis=0)
        centroids[category] = centroid.tolist()

    # Сохраняем центроиды в JSON
    with open(centroids_file, 'w', encoding='utf-8') as f:
        json.dump(centroids, f, ensure_ascii=False, indent=2)

    logger.info(f"Центроиды сохранены в {centroids_file}")


compute_centroids(os.path.join(STORAGE_PATH, 'examples_bn.json'),
                  os.path.join(STORAGE_PATH, 'centroids_bn.json'))
