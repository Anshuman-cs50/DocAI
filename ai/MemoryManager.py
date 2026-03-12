from sqlalchemy.orm import Session
from db import crud
from typing import List, Any
from . import embedding
from flask import jsonify
from . import LLM_module

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
    
    print(f"[DEBUG] Starting manage_consultation_memory for consultation_id: {consultation_id}")
    
    # 1. Retrieve entries since the last summary update
    try:
        unsummarized_entries = crud.get_unsummarized_timeline_entries(
            db, 
            consultation_id=consultation_id,
            limit=SUMMARY_UPDATE_THRESHOLD
        )
        print(f"[DEBUG] Retrieved {len(unsummarized_entries)} unsummarized entries (threshold: {SUMMARY_UPDATE_THRESHOLD})")
    except Exception as e:
        print(f"[ERROR] Failed to retrieve unsummarized entries: {str(e)}")
        return {"error": f"error retrieving unsummarized entries:\n {str(e)}"}

    # 2. Check the trigger condition
    if len(unsummarized_entries) >= SUMMARY_UPDATE_THRESHOLD:
        print(f"[DEBUG] Threshold reached. Proceeding with summarization.")
        
        # 3. Prepare context for the summarizer LLM
        try:
            context_to_summarize = format_timeline_for_summarization(unsummarized_entries)
            print(f"[DEBUG] Formatted context for summarization. Length: {len(context_to_summarize)}")
        except Exception as e:
            print(f"[ERROR] Failed to format context: {str(e)}")
            return {"error": f"error formatting context:\n {str(e)}"}
        
        # Get the existing summary (to pass to the summarizer for cumulative context)
        try:
            current_consultation = crud.get_consultation_by_id(db, consultation_id)
            if not current_consultation:
                raise ValueError(f"Consultation {consultation_id} not found")
            existing_summary = current_consultation.summary or "This is the start of the summary."
            print(f"[DEBUG] Retrieved existing summary. Length: {len(existing_summary)}")
        except Exception as e:
            print(f"[ERROR] Failed to retrieve consultation: {str(e)}")
            return {"error": f"error retrieving consultation:\n {str(e)}"}
        
        # 4. Call the Summarization LLM
        print(f"[DEBUG] Calling summarize LLM...")
        try:
            new_summary = data_processing_llm.summarise(existing_summary, context_to_summarize)
            print(f"[DEBUG] LLM returned summary. Length: {len(new_summary) if new_summary else 0}")
        except Exception as e:
            print(f"[ERROR] LLM summarization failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"error during LLM summarization:\n {str(e)}"}

        # 5. Generate the embedding for the NEW summary
        print(f"[DEBUG] Generating embedding for new summary...")
        try:
            new_embedding_vector = embedder.generate_embedding(new_summary)
            print(f"[DEBUG] Embedding generated. Shape: {new_embedding_vector.shape if hasattr(new_embedding_vector, 'shape') else 'unknown'}")
        except Exception as e:
            print(f"[ERROR] Failed to generate embedding: {str(e)}")
            return {"error": f"error generating embedding:\n {str(e)}"}

        # 6. Update the Consultation record
        print(f"[DEBUG] Updating consultation summary and embedding...")
        try:
            crud.update_consultation_summary_and_embedding(
                db,
                consultation_id=consultation_id,
                new_summary=new_summary,
                new_embedding_vector=new_embedding_vector
            )
            print(f"[DEBUG] Successfully updated consultation {consultation_id}")
        except Exception as e:
            print(f"[ERROR] Failed to update consultation: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"error updating consultation summary and embedding:\n {str(e)}"}
        
        print(f"[DEBUG] Summary update completed successfully")
        return {"message": f"Successfully updated summary for consultation {consultation_id}"}
    else:
        print(f"[DEBUG] Only {len(unsummarized_entries)} unsummarized entries. Threshold ({SUMMARY_UPDATE_THRESHOLD}) not reached. Skipping summary update.")
    
    return False