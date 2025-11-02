import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='tensorflow')

import time
import numpy as np
from typing import Dict, Any, List, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# --- Configuration & Model Initialization (CHANGE THIS LINE) ---
# Test Model 2: "intfloat/e5-large-v2"
# Test Model 3: "Alibaba-NLP/gte-large"
# Set to E5 for the rerun:
# EMBEDDING_MODEL_NAME = "emilyalsentzer/Bio_ClinicalBERT"
# EMBEDDING_MODEL_NAME = "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"

EMBEDDING_MODEL_NAME = "pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb"



try:
    # Adding trust_remote_code=True for potential large models like GTE
    model = SentenceTransformer(EMBEDDING_MODEL_NAME, trust_remote_code=True)
    EMBEDDING_DIMENSION = model.get_sentence_embedding_dimension() 

except Exception as e:
    print(f"Error loading Sentence Transformer model: {e}")
    model = None
    EMBEDDING_DIMENSION = 384 

def generate_embedding_for_condition(condition: Dict[str, Any]) -> List[float]:
    """
    Generates a dense vector embedding using the OPTIMAL Labeled Format,
    applying model-specific prompts where necessary.
    """
    if not model:
        return [0.0] * EMBEDDING_DIMENSION
        
    condition_name = condition.get('name', 'unknown condition')
    condition_type = condition.get('type', 'unspecified')
    notes = condition.get('notes', "")
    
    # 1. OPTIMAL TEXT CONSTRUCTION (Name/Type first, Notes last)
    embedding_text_core = (
        f"{condition_name} {condition_type} {notes}"
    )
    
    # call the model after setting trust_remote_code=True
    embedding_text = embedding_text_core
        
    # 3. GENERATE THE EMBEDDING
    try:
        embedding = model.encode(embedding_text, convert_to_tensor=False)
        return embedding.tolist()

    except Exception as e:
        print(f"Error encoding embedding for '{condition_name}': {e}")
        return [0.0] * EMBEDDING_DIMENSION 

def calculate_similarity(vector1: np.ndarray, vector2: np.ndarray) -> float:
    """
    Calculates Cosine Similarity between two vectors.
    """
    v1 = vector1.reshape(1, -1)
    v2 = vector2.reshape(1, -1)
    return cosine_similarity(v1, v2)[0][0]


if __name__ == "__main__":
    # 20 VAST TEST CASES (Unchanged)
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

    all_vectors = {}
    total_start_time = time.perf_counter()
    individual_times = []

    print(f"--- Running Test Suite: OPTIMAL LABELED FORMAT ({len(test_cases)} cases) ---")

    
    for case in test_cases:
        case_start_time = time.perf_counter()
        
        # Generate the embedding
        embedding_list = generate_embedding_for_condition(case)
        
        case_end_time = time.perf_counter()
        
        time_taken = case_end_time - case_start_time
        individual_times.append(time_taken)
        
        vector_length = len(embedding_list)
        
        if vector_length > 0 and embedding_list[0] != 0.0:
            all_vectors[case['id']] = np.array(embedding_list)
            # print(f"  ✅ Case #{case['id']:02d} - {case['name']:<30} | Status: Generated ({vector_length}D). Time: {time_taken:.4f}s") # Suppress for brevity
        else:
            print(f"  ❌ Case #{case['id']:02d} - {case['name']:<30} | Status: Failed. Time: {time_taken:.4f}s")

    # --- Performance Summary & Quality Check (Keep for context) ---
    total_end_time = time.perf_counter()
    total_time_taken = total_end_time - total_start_time
    average_time = sum(individual_times) / len(individual_times) if individual_times else 0.0
    
    # print("\n" + "="*70)
    # print("✨ **PERFORMANCE SUMMARY**")
    # print(f"| Total Conditions Processed: **{len(test_cases)}**")
    # print(f"| **Total Time Taken:** **{total_time_taken:.4f} seconds**")
    # print(f"| **Average Time Per Embedding:** **{average_time:.4f} seconds**")
    # print("="*70)

    print("\n## 🔬 Semantic Quality Check (Cosine Similarity - OPTIMAL FORMAT)")
    
    # 1. High Semantic Similarity Check (Very close concepts)
    if 1 in all_vectors and 20 in all_vectors:
        similarity_score_high = calculate_similarity(all_vectors[1], all_vectors[20])
        print(f"* **High Similarity Check:** 'Hypertension' (1) vs. 'High Blood Pressure' (20)")
        print(f"  > **Current Score (S):** **{similarity_score_high:.4f}**")
    
    # 2. Low Semantic Similarity Check (Distant concepts)
    if 5 in all_vectors and 9 in all_vectors:
        similarity_score_low = calculate_similarity(all_vectors[5], all_vectors[9])
        print(f"* **Low Similarity Check:** 'Acute Appendicitis' (5) vs. 'Generalized Anxiety Disorder' (9)")
        print(f"  > **Current Score (D):** **{similarity_score_low:.4f}**")
        
    print("\n" + "="*70)
    print("✨ **SCENARIO TEST: NATURAL LANGUAGE QUERY RETRIEVAL**")
    print("="*70)

    # --- SCENARIO TEST: Natural Language Query ---
    
    # Define the User's Natural Language Query (The "Search")
    # query_case = { 
    #     "id": 100, 
    #     "name": "Chronic Respiratory Symptoms", 
    #     "type": "Search Query", 
    #     "notes": "What is the diagnosis for a chronic condition causing wheezing and shortness of breath treated with an inhaler?"
    # }

    # Query Case 101: Acute, High-Urgency Search (Target: Acute Appendicitis, ID 5)
    # query_case = { 
    #     "id": 101, 
    #     "name": "Right Lower Quadrant Pain", 
    #     "type": "Search Query", 
    #     "notes": "A patient reports severe abdominal pain that started near the belly button and moved to the lower right side. We see a moderate fever."
    # }

    # Query Case 102: Chronic, Vague Symptoms Search (Target: Generalized Anxiety Disorder, ID 9)
    # query_case = { 
    #     "id": 102, 
    #     "name": "Uncontrollable Worry", 
    #     "type": "Search Query", 
    #     "notes": "Looking for a diagnosis characterized by persistent, excessive, and uncontrollable worry that is often managed with talk therapy."
    # }

    # Query Case 103: Procedure/Treatment-Focused Search (Target: Tibial Plateau Fracture, ID 14)
    query_case = { 
        "id": 103, 
        "name": "Surgical Fixation Injury", 
        "type": "Search Query", 
        "notes": "What medical case involves a lower leg injury from a fall that required plates and screws for internal fixation, and a non-weight-bearing restriction?"
    }

    # Generate the embedding for the query
    query_vector_list = generate_embedding_for_condition(query_case)
    query_vector = np.array(query_vector_list)

    # Calculate similarity to all knowledge base vectors
    similarity_results = []
    
    for case in test_cases:
        if case['id'] in all_vectors:
            knowledge_vector = all_vectors[case['id']]
            score = calculate_similarity(query_vector, knowledge_vector)
            similarity_results.append({
                "name": case['name'],
                "type": case['type'],
                "score": score
            })

    # Sort and print the top 3 results
    similarity_results.sort(key=lambda x: x['score'], reverse=True)

    print(f"**Query:** {query_case['notes']}\n")
    print(f"| Rank | Condition Name | Type | Similarity Score |")
    print(f"| :---: | :--- | :--- | :---: |")

    for i, result in enumerate(similarity_results[:5]):
        print(f"| {i+1:<4} | {result['name']:<20} | {result['type']:<20} | **{result['score']:.4f}** |")

    print("\n--- Scenario Test Complete ---")