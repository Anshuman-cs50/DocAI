import numpy as np

from db import crud
from .embedding import MedicalEmbedder
from .LLM_module import ConsultationLLM, DataProcessingLLM, ExtractionInsights

# initialising LLM models and embedder (module-level singletons)
# routes.py can access these directly for hot-reloading, e.g. ai.consultation_llm.update_gradio_url(url)
consultation_llm = ConsultationLLM()
data_processing_llm = DataProcessingLLM()
embedder = MedicalEmbedder()


# ------------- Helper: format timeline context -------------------
def format_timeline_context(timeline_entries: list) -> str:
    """Formats the consultation timeline history into a clean, chronological string."""
    context = ""
    for entry in timeline_entries:
        # Assuming entry has user_query and model_response attributes
        context += f"USER: {entry.user_query}\n"
        context += f"MODEL: {entry.model_response}\n\n"
    return context.strip()


# ------------- Helper: format health records context -------------------
def format_health_records_context(health_records: list) -> str:
    """Formats the semantically retrieved health records for LLM consumption."""
    context_lines = []
    
    # Each record is a dictionary from the semantic_search_records function
    for i, record in enumerate(health_records):
        
        # Determine the type of record for a clear header
        header = f"--- [{i+1}] {record['type']} - {record['title']} ---"
        
        # Format the record details
        details = (
            f"Date: {record['date']}\n"
            f"Source Snippet: {record['snippet']}"
        )
        context_lines.append(f"{header}\n{details}")
        
    return "\n\n".join(context_lines)


# ------------- Main consultation response ----------------
def generate_consultation_response(
    db, 
    user_id: int, 
    consultation_id: int, 
    user_query: str, 
):     
    """
    Orchestrates the ReAct dual-pass agentic loop for a consultation response.
    """
    # Get metadata about the *current* consultation session
    current_consultation = crud.get_consultation_by_id(db, consultation_id)
    
    current_consultation_context = ""
    if current_consultation:
        current_consultation_context = (
            f"Current Session Heading: {current_consultation.heading}\n"
            f"Current Session Start Date: {current_consultation.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    # 1. Get consultation timeline history for session context (longer native history)
    consultation_timeline_entries = crud.get_recent_timeline_entries(
        db,
        consultation_id=consultation_id,
        limit=20
    )
    
    from .MemoryManager import format_timeline_as_messages
    from .LLM_module import AGENTIC_SYSTEM_PROMPT
    
    messages = format_timeline_as_messages(consultation_timeline_entries)
    
    system_prompt = AGENTIC_SYSTEM_PROMPT.format(current_consultation_context=current_consultation_context)
    
    if len(messages) == 0:
        messages.append({"role": "user", "content": system_prompt + "\n\nUser Query:\n" + user_query})
    else:
        # Prepend to the very first history message to anchor the persona
        messages[0]["content"] = system_prompt + "\n\n" + messages[0]["content"]
        messages.append({"role": "user", "content": user_query})

    # Pass 1: Decision Mode
    print(f"[STEP] Agent Pass 1 (Decision Mode)...")
    model_response = consultation_llm.agentic_chat(messages)
    
    user_health_records_context = ""
    combined_response = ""
    
    if "[SEARCH]" in model_response:
        search_query = model_response.split("[SEARCH]")[-1].strip()
        print(f"[STEP] Agent requested SEARCH for: '{search_query}'")
        
        # 2. Generate embedding for the search query
        query_embedding = embedder.generate_embedding(search_query)
        if not isinstance(query_embedding, np.ndarray):
            query_embedding = np.array(query_embedding)
        query_embedding = query_embedding.flatten().tolist()
        
        # 3. Get relevant user health records
        user_health_records = crud.semantic_search_records(
            db, 
            user_id=user_id, 
            query_embedding=query_embedding,
            current_consultation_id=consultation_id,
            k_consultations=4,
        )
        user_health_records_context = format_health_records_context(user_health_records)
        if not user_health_records_context:
            user_health_records_context = "No results found for that search query."
            
        # 4. Append the context to the messages as a "System" observation
        observation = f"System Search Results:\n{user_health_records_context}\nPlease [ANSWER] now."
        messages.append({"role": "model", "content": model_response})
        messages.append({"role": "user", "content": observation})
        
        # Pass 2: Answering Mode
        print(f"[STEP] Agent Pass 2 (Answering Mode)...")
        final_answer = consultation_llm.agentic_chat(messages)
        
        if "[ANSWER]" in final_answer:
            final_answer = final_answer.split("[ANSWER]")[-1].strip()
            
        combined_response = f"[SEARCH] {search_query}\n\n[SYSTEM] Search Result injected:\n{user_health_records_context}\n\n[ANSWER] {final_answer}"

    elif "[ASK]" in model_response:
        # The model wants live input from the patient — a lifestyle/symptom question
        # that the DB cannot answer. Surface it directly to the patient as a response.
        # No DB call, no second pass. The patient's reply will arrive in the next turn,
        # at which point the model can act on it.
        asked_question = model_response.split("[ASK]")[-1].strip()
        print(f"[STEP] Agent asking patient: '{asked_question}'")
        combined_response = f"[ASK] {asked_question}"
        
    else:
        # It chose to answer directly (or hallucinated)
        final_answer = model_response
        if "[ANSWER]" in final_answer:
            final_answer = final_answer.split("[ANSWER]")[-1].strip()
        print(f"[STEP] Agent chose to answer directly.")
        combined_response = f"[ANSWER] {final_answer}"
        
    # 6. Return response and context
    return {
        "model_response": combined_response,
        "timeline_context": "Native Message History Array Used",
        "user_health_records_context": user_health_records_context
    }


# ------------- Extract insights from response ----------------
def extract_insights(user_query: str, model_response: str) -> ExtractionInsights:
    """
    Uses an LLM to generate a concise, high-density insight from a single 
    user-model turn for vector indexing.

    Args:
        user_query: The text the user submitted.
        model_response: The text the model responded with.

    Returns:
        ExtractionInsights object with insight details, or default if LLM fails.
    """

    try:
        # Call the insights extraction LLM
        insights: ExtractionInsights = data_processing_llm.extract_insights(
            user_query=user_query,
            model_response=model_response
        )
        return insights
    
    except Exception as e:
        print(f"[WARNING] Failed to extract insights: {str(e)}")
        # Return default ExtractionInsights on failure
        return ExtractionInsights(
            insight_found=False,
            compressed_summary="",
            primary_condition_or_symptom="",
            icd_codes_extracted=[]
        )

