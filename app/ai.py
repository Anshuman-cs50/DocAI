from db.crud import semantic_search, add_timeline_entry

# ------------- Helper: Generate embedding ----------------
def generate_embedding(embedding_model, text: str) -> list:
    """
    Generate embedding vector for given text using embedding_model.
    """
    # TODO: Implement actual embedding generation logic
    return embedding_model.embed(text)  # Should return a list of floats



# ------------- Helper: Build context -------------------
def build_context(past_entries: list) -> str:
    """
    Build string context for AI prompt from past consultations.
    """
    context = "\n\n".join([
        f"Previous Query: {e['user_query']}\nResponse: {e['model_response']}"
        for e in past_entries
    ])
    return context



# ------------- Main consultation response ----------------
def generate_consultation_response(db, user_id: int, consultation_id: int, user_query: str, embedding_model, llm_model):
    """
    Retrieve relevant past entries, generate response using LLM, and return response + context.
    """
    # Generate embedding for the query
    query_embedding = generate_embedding(embedding_model, user_query)

    # Retrieve top-k similar past consultations
    past_entries = semantic_search(db, user_id, query_embedding, top_k=3)

    # Build context string
    context = build_context(past_entries)

    # Compose LLM prompt
    prompt = f"Relevant past consultations:\n{context}\n\nUser Query:\n{user_query}"
    model_output = llm_model.generate(prompt)  # Replace with your MedGemma call

    # Return model response + past context used
    return {
        "response": model_output,
        "context_used": past_entries,
    }
