import os
import requests
import numpy as np
from typing import Dict, Any, List

class MedicalEmbedder:
    """
    Handles embedding generation using the HuggingFace Inference API.
    Implemented as a singleton to avoid multiple initializations.
    Outsourced from local sentence-transformers to save RAM.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_name: str = "pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb"):
        if not hasattr(self, 'dimension'):
            self.model_name = model_name
            self.dimension = int(os.environ.get("VECTOR_DIMENSION", 768))
            self.api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_name}"
            
            hf_token = os.environ.get("HF_API_TOKEN")
            if not hf_token:
                print("[WARN] HF_API_TOKEN not found. Embeddings will fail.")
            self.headers = {"Authorization": f"Bearer {hf_token}"}
            print(f"[OK] MedicalEmbedder initialized to use HF API: {self.model_name} ({self.dimension}D)")

    def _call_hf_api(self, text: str) -> np.ndarray:
        try:
            response = requests.post(
                self.api_url, 
                headers=self.headers, 
                json={"inputs": text},
                timeout=15
            )
            if response.status_code != 200:
                print(f"[ERROR] HF API returned {response.status_code}: {response.text}")
                return np.array([0.0] * self.dimension)

            data = response.json()
            
            # Sentence transformers usually return a 1D array of size 768 for a single string.
            # If it's nested (e.g. [[768]]), we'll flatten it safely.
            def flatten(lst):
                flat = []
                for item in lst:
                    if isinstance(item, list):
                        flat.extend(flatten(item))
                    else:
                        flat.append(item)
                return flat

            if isinstance(data, list):
                flat_data = flatten(data)
                
                # If HF returns token-level embeddings (e.g., shape [seq_len, 768]), 
                # we should mean pool it.
                if len(flat_data) > self.dimension and len(flat_data) % self.dimension == 0:
                    arr = np.array(flat_data).reshape(-1, self.dimension)
                    return np.mean(arr, axis=0)
                elif len(flat_data) >= self.dimension:
                    return np.array(flat_data[:self.dimension])
                else:
                    print(f"[ERROR] Expected {self.dimension} dims, got {len(flat_data)}")
                    return np.array([0.0] * self.dimension)
            else:
                print(f"[ERROR] Unexpected format from HF: {type(data)}")
                return np.array([0.0] * self.dimension)
                
        except Exception as e:
            print(f"[ERROR] Error calling HF API: {e}")
            return np.array([0.0] * self.dimension)

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generates embedding for the given text."""
        return self._call_hf_api(text)

    def generate_embedding_for_condition(self, condition: Dict[str, Any]) -> np.ndarray:
        """
        Generates the LONG, DESCRIPTIVE vector for the Knowledge Base and Search Queries.
        Format: {notes} {name} {type} (Optimal for contextual search recall).
        """
        condition_name = condition.get('name', 'unknown condition')
        condition_type = condition.get('type', 'unspecified')
        notes = condition.get('notes', "")
        
        # LONG FORMAT CONSTRUCTION
        embedding_text = f"{notes} {condition_name} {condition_type}"
        return self._call_hf_api(embedding_text)

    def generate_high_focus_embedding(self, condition: Dict[str, Any]) -> List[float]:
        """
        Generates the SHORT, HIGH-FOCUS vector for Synonymy Checks (S-Score).
        Format: The patient has {name}. (Optimal for synonym precision).
        """
        condition_name = condition.get('name', 'unknown condition')
        
        # HIGH-FOCUS CONSTRUCTION
        embedding_text = f"The patient has {condition_name}."
        arr = self._call_hf_api(embedding_text)
        return arr.tolist()

# --- Utility Functions (Outside the Class) ---

def calculate_similarity(vector1: np.ndarray, vector2: np.ndarray) -> float:
    """Calculates Cosine Similarity between two vectors manually to avoid sklearn."""
    dot_product = np.dot(vector1, vector2)
    norm1 = np.linalg.norm(vector1)
    norm2 = np.linalg.norm(vector2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
        
    return float(dot_product / (norm1 * norm2))

# --- Main Execution Block ---

if __name__ == "__main__":
    import sys
    # Quick test
    from dotenv import load_dotenv
    load_dotenv("../.env")
    
    print("\n--- Testing API Embdder ---")
    embedder = MedicalEmbedder()
    
    text = "Patient presents with acute appendicitis."
    print(f"Generating embedding for: '{text}'")
    vec = embedder.generate_embedding(text)
    
    print(f"Generated Vector Shape: {vec.shape}")
    print(f"Sample values (first 5): {vec[:5]}")
    
    if vec.shape == (768,) and not np.all(vec == 0):
        print("\n[SUCCESS] Embedder API call works perfectly!")
    else:
        print("\n[FAIL] Embedder did not return expected 768D vector.")
        sys.exit(1)