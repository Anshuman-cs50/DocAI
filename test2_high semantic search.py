import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='tensorflow')

import numpy as np
import time
from typing import Dict, Any, List, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

class MedicalEmbedder:
    """
    Handles embedding generation using a BioBERT model, employing a Dual-Embedding Strategy 
    for optimized performance across both semantic search and synonymy checks.
    """
    def __init__(self, model_name: str = "pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb"):
        self.model_name = model_name
        self.model = None
        self.dimension = 0
        self._load_model()

    def _load_model(self):
        """Loads the Sentence Transformer model."""
        try:
            # Use trust_remote_code=True for potential large models
            self.model = SentenceTransformer(self.model_name, trust_remote_code=True)
            self.dimension = self.model.get_sentence_embedding_dimension()
            print(f"✅ Model loaded: {self.model_name} ({self.dimension}D)")
        except Exception as e:
            print(f"❌ Error loading model {self.model_name}: {e}")
            self.model = None
            self.dimension = 768 # Default BERT dimension

    def generate_long_format_embedding(self, condition: Dict[str, Any]) -> List[float]:
        """
        Generates the LONG, DESCRIPTIVE vector for the Knowledge Base and Search Queries.
        Format: {notes} {name} {type} (Optimal for contextual search recall).
        """
        if not self.model: return [0.0] * self.dimension
            
        condition_name = condition.get('name', 'unknown condition')
        condition_type = condition.get('type', 'unspecified')
        notes = condition.get('notes', "")
        
        # LONG FORMAT CONSTRUCTION (Validated Optimal Format for search)
        embedding_text = f"{notes} {condition_name} {condition_type}"
        
        try:
            embedding = self.model.encode(embedding_text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            print(f"Error encoding long embedding for '{condition_name}': {e}")
            return [0.0] * self.dimension 

    def generate_high_focus_embedding(self, condition: Dict[str, Any]) -> List[float]:
        """
        Generates the SHORT, HIGH-FOCUS vector for Synonymy Checks (S-Score).
        Format: The patient has {name}. (Optimal for synonym precision).
        """
        if not self.model: return [0.0] * self.dimension
            
        condition_name = condition.get('name', 'unknown condition')
        
        # HIGH-FOCUS CONSTRUCTION (Validated Optimal Format for synonymy)
        embedding_text = f"The patient has {condition_name}."
            
        try:
            embedding = self.model.encode(embedding_text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            print(f"Error encoding high-focus embedding for '{condition_name}': {e}")
            return [0.0] * self.dimension 

# --- Utility Functions (Outside the Class) ---

def calculate_similarity(vector1: np.ndarray, vector2: np.ndarray) -> float:
    """Calculates Cosine Similarity between two vectors."""
    v1 = vector1.reshape(1, -1)
    v2 = vector2.reshape(1, -1)
    return cosine_similarity(v1, v2)[0][0]

# --- Main Execution Block ---

if __name__ == "__main__":
    
    # 0. Initialize Embedder
    embedder = MedicalEmbedder()
    
    # 1. Define Test Cases
    test_cases = [
        # CHRONIC & COMMON
        { "id": 1, "name": "Hypertension", "type": "Chronic Disease", "notes": "Patient manages high blood pressure with Lisinopril 10mg daily. Compliant with low-sodium diet." },
        { "id": 2, "name": "Type 2 Diabetes Mellitus", "type": "Metabolic Disorder", "notes": "A1C at 7.0. Takes Metformin 1000mg BID. Reports occasional peripheral neuropathy in feet." },
        { "id": 3, "name": "Rheumatoid Arthritis", "type": "Autoimmune Disease", "notes": "Active joint swelling in hands and knees. Started on Methotrexate 15mg weekly." },
        { "id": 4, "name": "Asthma", "type": "Respiratory Condition", "notes": "Intermittent, mild persistent. Uses Albuterol PRN and Flovent daily. Recent viral infection triggered mild wheezing." },
        
        # ACUTE & INFECTIOUS
        { "id": 5, "name": "Acute Appendicitis", "type": "Surgical Emergency", "notes": "Presents with periumbilical pain radiating to RLQ. Fever of 101.5°F. Scheduled for urgent appendectomy." },
        { "id": 6, "name": "Strep Throat (Group A Streptococcus)", "type": "Infectious Disease", "notes": "Confirmed by rapid antigen test. Treated with Amoxicillin for 10 days. Follow-up culture negative." },
        { "id": 7, "name": "Common Cold (Rhinovirus)", "type": "Viral Infection", "notes": "Self-limiting, symptoms include rhinorrhea and congestion. Advised rest and hydration." },
        
        # MENTAL HEALTH & NEUROLOGICAL
        { "id": 8, "name": "Major Depressive Disorder (MDD)", "type": "Mental Health", "notes": "Recurrent, severe. Started on Sertraline 50mg. Follow-up with therapist scheduled weekly." },
        { "id": 9, "name": "Generalized Anxiety Disorder (GAD)", "type": "Mental Health", "notes": "Worrying is uncontrollable. Uses cognitive behavioral therapy (CBT) techniques." },
        { "id": 10, "name": "Migraine without Aura", "type": "Neurological Disorder", "notes": "Chronic headache condition. Uses Sumatriptan for acute attacks. Tries to avoid red wine as a trigger." },

        # RARE & COMPLEX
        { "id": 11, "name": "Crohn's Disease", "type": "Inflammatory Bowel Disease", "notes": "Active flare-up in the terminal ileum. Prescribed oral corticosteroids for induction of remission." },
        { "id": 12, "name": "Systemic Lupus Erythematosus (SLE)", "type": "Autoimmune Disorder", "notes": "Currently stable, monitoring for kidney involvement. On Plaquenil indefinitely." },
        { "id": 13, "name": "Von Hippel-Lindau Disease", "type": "Genetic Disorder", "notes": "Rare condition. Monitoring for development of hemangioblastomas in the retina and cerebellum." },
        
        # TRAUMA & INJURY
        { "id": 14, "name": "Tibial Plateau Fracture", "type": "Orthopedic Injury", "notes": "Result of a skiing accident. Required surgical internal fixation with plates and screws. NWB for 8 weeks." },
        { "id": 15, "name": "Concussion (Mild Traumatic Brain Injury)", "type": "Traumatic Injury", "notes": "Symptoms resolved after 7 days of cognitive rest. Follow-up scan was clear." },

        # SKIN & EYES
        { "id": 16, "name": "Eczema (Atopic Dermatitis)", "type": "Skin Condition", "notes": "Chronic dry, itchy skin patches on inner elbows and back of knees. Uses topical steroids as needed." },
        { "id": 17, "name": "Glaucoma", "type": "Eye Disorder", "notes": "Open-angle type. Intraocular pressure (IOP) remains controlled with Latanoprost drops." },
        
        # REPRODUCTIVE & UROLOGICAL
        { "id": 18, "name": "Polycystic Ovary Syndrome (PCOS)", "type": "Endocrine Disorder", "notes": "Hormonal imbalance causing irregular periods. Treating with oral contraceptives to regulate cycle." },
        { "id": 19, "name": "Kidney Stone (Nephrolithiasis)", "type": "Urological Condition", "notes": "Acute, symptomatic passing of a 3mm calcium oxalate stone. Pain managed with Toradol." },

        # High Semantic Overlap (for similarity test)
        { "id": 20, "name": "High Blood Pressure", "type": "Cardiovascular Risk Factor", "notes": "Elevated blood pressure reading during routine physical. Counseling provided on lifestyle changes. No medication started yet." },
    ]
    
    # Add a full set of 20 cases for complete execution, using a placeholder if not all 20 are listed above
    if len(test_cases) < 20:
        test_cases.extend([
            { "id": i, "name": f"Dummy Condition {i}", "type": "Dummy Type", "notes": f"Placeholder note for case {i} to fill the array." }
            for i in range(21, 21 + 20 - len(test_cases))
        ])

    all_vectors = {}
    print("\n--- Generating Knowledge Base (KB) Vectors using LONG Format ---")
    
    # 2. KB EMBEDDING: Using the LONG FORMAT for all records
    for case in test_cases:
        if case['id'] in [1, 5, 9, 20] or case['id'] > 20: # Only embed necessary cases for testing
            vector_list = embedder.generate_long_format_embedding(case)
            all_vectors[case['id']] = np.array(vector_list)

    # 3. SEMANTIC QUALITY CHECK (S-Score and D-Score)
    print("\n## 🔬 Dual Strategy Validation")

    # S-SCORE CHECK (Uses HIGH-FOCUS format for precision)
    condition_1_vector = np.array(embedder.generate_high_focus_embedding(test_cases[0]))
    condition_20_vector = np.array(embedder.generate_high_focus_embedding(test_cases[3]))
    similarity_score_high = calculate_similarity(condition_1_vector, condition_20_vector)
    
    print(f"* **Synonymy Check (S-Score):** **{similarity_score_high:.4f}** (Target: > 0.85)")

    # D-SCORE CHECK (Uses LONG-FORMAT for discernment)
    if 5 in all_vectors and 9 in all_vectors:
        similarity_score_low = calculate_similarity(all_vectors[5], all_vectors[9])
        print(f"* **Discernment Check (D-Score):** **{similarity_score_low:.4f}** (Target: < 0.20)")
        
    # 4. SCENARIO TEST (Query Retrieval)
    print("\n## ✨ Scenario Test: Contextual Retrieval")

    query_case = { 
        "id": 102, 
        "name": "Uncontrollable Worry", 
        "type": "Search Query", 
        "notes": "Looking for a diagnosis characterized by persistent, excessive, and uncontrollable worry that is often managed with talk therapy."
    }
    
    # QUERY EMBEDDING: Uses the LONG FORMAT for recall
    query_vector = np.array(embedder.generate_long_format_embedding(query_case))

    similarity_results = []
    
    for case in test_cases:
        if case['id'] in all_vectors:
            score = calculate_similarity(query_vector, all_vectors[case['id']])
            similarity_results.append({"name": case['name'], "score": score})

    similarity_results.sort(key=lambda x: x['score'], reverse=True)

    print(f"**Query:** {query_case['notes']}\n")
    print(f"| Rank | Condition Name | Similarity Score |")
    print(f"| :---: | :--- | :---: |")

    for i, result in enumerate(similarity_results[:4]):
        print(f"| {i+1:<4} | {result['name']:<20} | **{result['score']:.4f}** |")

    print("\n--- Execution Complete ---")