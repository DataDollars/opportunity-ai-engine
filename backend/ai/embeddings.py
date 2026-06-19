import logging
import hashlib
import math
import httpx
from typing import List, Optional
from backend.config import settings

logger = logging.getLogger(__name__)

HF_API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"

def get_sin_hash_embedding(text: str, dimension: int = 384) -> List[float]:
    """
    Generates a deterministic 384-dimensional unit vector using word-level sin-hash
    and domain-specific synonym grouping to mimic semantic proximity offline.
    """
    if not text:
        return [0.0] * dimension

    SYNONYM_GROUPS = {
        "agriculture": ["agri", "farming", "farmer", "crop", "cultivation", "harvest", "kisan", "agro"],
        "technology": ["tech", "software", "digital", "it", "cloud", "computer", "internet", "upgradation", "adoption"],
        "finance": ["funding", "loan", "grant", "subsidy", "credit", "money", "capital", "assistance"],
        "textiles": ["weaver", "handloom", "textile", "garment", "apparel", "cloth"],
        "manufacturing": ["factory", "industrial", "machinery", "production"]
    }
    
    # Reverse mapping for fast lookup
    word_to_rep = {}
    for rep, synonyms in SYNONYM_GROUPS.items():
        word_to_rep[rep] = rep
        for syn in synonyms:
            word_to_rep[syn] = rep
            
    # Simple preprocessing
    text_clean = "".join(c for c in text.lower() if c.isalnum() or c.isspace())
    words = text_clean.split()
    
    total_vector = [0.0] * dimension
    seen_reps = set()
    
    import random
    
    for word in words:
        # Resolve to representative or use original word
        rep_word = word_to_rep.get(word, word)
        if rep_word in seen_reps:
            continue
        seen_reps.add(rep_word)
        
        # Word level hash vector using python's Random
        hasher = hashlib.sha256(rep_word.encode("utf-8"))
        seed = int.from_bytes(hasher.digest()[:8], byteorder="big")
        rng = random.Random(seed)
        for i in range(dimension):
            total_vector[i] += rng.uniform(-1.0, 1.0)
            
        # Character 3-grams to handle small morphological variations for non-synonym words
        if rep_word not in SYNONYM_GROUPS and len(rep_word) >= 3:
            for j in range(len(rep_word) - 2):
                ngram = rep_word[j:j+3]
                ngram_hasher = hashlib.sha256(ngram.encode("utf-8"))
                ngram_seed = int.from_bytes(ngram_hasher.digest()[:8], byteorder="big")
                ngram_rng = random.Random(ngram_seed)
                for i in range(dimension):
                    total_vector[i] += 0.2 * ngram_rng.uniform(-1.0, 1.0)
                    
    # Normalize to unit L2 norm
    norm = math.sqrt(sum(v * v for v in total_vector))
    if norm > 0:
        return [v / norm for v in total_vector]
    return [0.0] * dimension

async def get_embedding(text: str) -> List[float]:
    """
    Generates a 384-dimensional embedding vector for the given text.
    Tries to use the Hugging Face Inference API if HUGGINGFACE_API_KEY is available.
    Falls back to a deterministic offline sin-hash embedding if HF is unavailable or fails.
    """
    if not text:
        return [0.0] * 384
        
    if settings.HUGGINGFACE_API_KEY:
        try:
            headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    HF_API_URL,
                    headers=headers,
                    json={"inputs": text}
                )
                if response.status_code == 200:
                    embedding = response.json()
                    # Sometimes HF returns a list of lists or a single list
                    if isinstance(embedding, list):
                        if len(embedding) > 0 and isinstance(embedding[0], list):
                            embedding = embedding[0]
                        if len(embedding) == 384:
                            # Normalize the vector to unit L2 norm for consistency
                            norm = math.sqrt(sum(v * v for v in embedding))
                            if norm > 0:
                                return [v / norm for v in embedding]
                            return embedding
                    logger.warning(f"Unexpected response structure from Hugging Face: {embedding}")
                else:
                    logger.warning(
                        f"Hugging Face API returned status {response.status_code}: {response.text}. "
                        "Using sin-hash fallback."
                    )
        except Exception as e:
            logger.warning(f"Failed to fetch embedding from Hugging Face: {e}. Using sin-hash fallback.")
            
    # Deterministic offline fallback
    return get_sin_hash_embedding(text)

def compute_cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Computes the cosine similarity between two vectors.
    """
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(x * y for x, y in zip(v1, v2))
    norm1 = math.sqrt(sum(x * x for x in v1))
    norm2 = math.sqrt(sum(x * x for x in v2))
    if norm1 > 0 and norm2 > 0:
        return dot_product / (norm1 * norm2)
    return 0.0
