from sqlalchemy.orm import Session
from db import crud
from typing import List, Any
import embedding
from flask import jsonify

llm_summariser = ...

# Define the minimum number of turns that must pass before re-summarization is triggered
SUMMARY_UPDATE_THRESHOLD = 10 

def format_timeline_for_summarization(timeline_entries: List[Any]) -> str:
    """
    Formats a list of ConsultationTimeline entries into a clean string 
    for the summarizer LLM to process.
    """
    context = "--- Conversation Timeline to Summarize ---\n"
    for entry in timeline_entries:
        # Assuming entry has user_query and model_response attributes
        context += f"USER ({entry.created_at.strftime('%H:%M')}): {entry.user_query}\n"
        context += f"MODEL ({entry.created_at.strftime('%H:%M')}): {entry.model_response}\n\n"
    return context.strip()


def manage_consultation_memory(
    db: Session,
    consultation_id: int
):
    """
    Checks if a consultation's summary is due for an update based on the number
    of new timeline entries, triggers summarization, and updates the database.
    
    Returns True if the summary was updated, False otherwise.
    """
    
    # 1. Retrieve entries since the last summary update
    unsummarized_entries = crud.get_unsummarized_timeline_entries(
        db, 
        consultation_id=consultation_id,
        limit=SUMMARY_UPDATE_THRESHOLD
    )

    # 2. Check the trigger condition
    if len(unsummarized_entries) >= SUMMARY_UPDATE_THRESHOLD:
        
        # 3. Prepare context for the summarizer LLM
        context_to_summarize = format_timeline_for_summarization(unsummarized_entries)
        
        # Get the existing summary (to pass to the summarizer for cumulative context)
        current_consultation = crud.get_consultation_by_id(db, consultation_id)
        existing_summary = current_consultation.summary or "This is the start of the summary."
        
        summarizer_prompt = f"""
        You are a clinical summarization engine. Your task is to update the 'EXISTING SUMMARY' 
        by incorporating the new information from the 'CONVERSATION TIMELINE'.
        
        The final summary must be concise, clinically relevant, and accurately reflect all key facts.

        --- EXISTING SUMMARY ---
        {existing_summary}
        
        --- CONVERSATION TIMELINE ---
        {context_to_summarize}
        
        --- NEW CUMULATIVE SUMMARY (Start with key points) ---
        """
        
        # 4. Call the Summarization LLM
        new_summary = llm_summariser.summarise(summarizer_prompt) 

        # 5. Generate the embedding for the NEW summary
        new_embedding_vector = embedding.generate_embedding(new_summary)

        # 6. Update the Consultation record
        try:
            crud.update_consultation_summary_and_embedding(
                db,
                consultation_id=consultation_id,
                new_summary=new_summary,
                new_embedding_vector=new_embedding_vector
            )
        except Exception as e:
            return jsonify({"error": f"error updating consultation summary and embedding:\n {str(e)}"})
        
        return jsonify({"success": f"Successfully updated summary for consultation {consultation_id}"})
    
    return jsonify({"message": f"summary up-to-date. no need for updation"})