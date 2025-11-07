from sqlalchemy.orm import Session
from db import crud
from typing import List, Any
import embedding
from flask import jsonify
from ai import LLM_module

embedder = embedding.MedicalEmbedder()
data_processing_llm = LLM_module.DataProcessingLLM()
# Define the minimum number of turns that must pass before re-summarization is triggered
SUMMARY_UPDATE_THRESHOLD = 10 

def format_timeline_for_summarization(timeline_entries: List[Any]) -> str:
    """
    Formats a list of ConsultationTimeline entries into a clean string 
    for the summarizer LLM to process.
    """
    context = ""
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
        
        # 4. Call the Summarization LLM
        new_summary = data_processing_llm.summarise(existing_summary, context_to_summarize) 

        # 5. Generate the embedding for the NEW summary
        new_embedding_vector = embedder.generate_embedding(new_summary)

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
        
        return jsonify({"message": f"Successfully updated summary for consultation {consultation_id}"})
    
    return False