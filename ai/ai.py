from db import crud
import embedding


llm_model = ...  # e.g., MedGemma model instance
llm_summariser = ...


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
    Generates a consultation response using LLM, informed by historical and session context.
    """
    
    # 1. Generate embedding for user query
    query_embedding = embedding.generate_embedding(user_query)

    # 2. Get relevant user health records (Consultation Summaries and Permanent Conditions)
    user_health_records = crud.semantic_search_records(
        db, 
        user_id=user_id, 
        query_embedding=query_embedding,
        current_consultation_id=consultation_id,
        k_consultations=3, # Increased to 3 for more context if needed
    )

    # 3. Get consultation timeline history for session context
    consultation_timeline_entries = crud.get_recent_timeline_entries(
        db,
        consultation_id=consultation_id,
        limit=5
    )
    
    # Get metadata about the *current* consultation session
    current_consultation = crud.get_consultation_by_id(db, consultation_id)
    
    # 4. Build context strings
    timeline_context = format_timeline_context(consultation_timeline_entries)
    user_health_records_context = format_health_records_context(user_health_records)
    
    current_consultation_context = ""
    if current_consultation:
        current_consultation_context = (
            f"Current Session Heading: {current_consultation.heading}\n"
            f"Current Session Start Date: {current_consultation.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Current Session Summary: {current_consultation.summary or 'No current summary available.'}"
        )

    # 5. Construct prompt for LLM
    prompt = f"""
    You are an AI Medical Assistant providing guidance to a user. 
    Your goal is to provide a helpful, concise, and clinically responsible response 
    based *only* on the provided context and the user's current query.
    
    --- CONTEXT: CURRENT SESSION METADATA ---
    {current_consultation_context}
    
    --- CONTEXT: CURRENT SESSION HISTORY (Last 5 Turns) ---
    {timeline_context or 'No prior history in this session.'}
    
    --- CONTEXT: HISTORICAL HEALTH RECORDS (Semantic Search Results) ---
    The following records are the most relevant historical health records to the user's query:
    {user_health_records_context or 'No highly relevant historical records found.'}
    
    --- USER QUERY ---
    {user_query}
    
    --- YOUR RESPONSE ---
    Based on the context and the user's query, provide your response.
    """
    
    # 6. Generate response from med LLM 
    model_response = llm_model.generate_response(prompt)

    # 7. Return response and context
    return {
        "model_response": model_response,
        "timeline_context": timeline_context,
        "user_health_records_context": user_health_records_context
    }


# ------------- Extract insights from response ----------------
def extract_insights(user_query: str, model_response: str) -> str:
    """
    Uses an LLM to generate a concise, high-density insight from a single 
    user-model turn for vector indexing.

    Args:
        user_query: The text the user submitted.
        model_response: The text the model responded with.
        llm_summarizer: The function/client wrapper for the summarization LLM.

    Returns:
        A concise string summarizing the key finding of this turn (max 2 sentences).
    """
    
    insight_prompt = f"""
    You are an extremely concise clinical insight extractor. Your task is to analyze 
    the following user query and model response, and distill the single, most 
    important piece of factual or clinical information discussed in this exchange. 
    
    The output MUST be a single, short sentence and MUST NOT include any conversational 
    phrasing like 'The user asked' or 'The model replied'. Just state the fact.

    --- EXCHANGE ---
    User: "{user_query}"
    Model: "{model_response}"

    --- KEY CLINICAL INSIGHT ---
    """

    # Call the summarization LLM
    # NOTE: You may use a different LLM instance here (e.g., gemini-2.5-flash)
    # for speed, as this runs synchronously during the consultation.
    
    # Placeholder for actual LLM call
    insights = llm_summariser.summarise(insight_prompt).strip()
    
    # Ensure the result is clean (e.g., remove quotes or leading/trailing whitespace)
    return insights.strip()


