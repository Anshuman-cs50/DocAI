from sqlalchemy.orm import Session
from sqlalchemy import func
from db import crud
from flask import jsonify
from . import embedding
from typing import List
from .LLM_module import ConditionAction, DataProcessingLLM

data_processing_llm = DataProcessingLLM()
embedder = embedding.MedicalEmbedder()

# (Threshold removed to support End-of-Session processing)

def check_and_log_user_conditions(
    db: Session,
    consultation_id: int,
    user_health_records_context: str
):
    """
    Checks for new user conditions based on the last condition check time.
    Returns a consistent dict format.
    """
    
    # get the last condition check time
    try:
        last_check_time = crud.get_last_condition_check_time(db, consultation_id)
    except Exception as e:
        return {
            "success": False,
            "message": "Error retrieving consultation check time.",
            "details": None,
            "errors": [str(e)]
        }
    
    if last_check_time is None:
        return {
            "success": False,
            "message": "Consultation not found.",
            "details": None,
            "errors": ["Consultation ID does not exist."]
        }
    
    # check if enough timeline entries have been added since last check
    try:
        new_entries = crud.get_timeline_entries_since(
            db,
            consultation_id,
            since=last_check_time
        )
    except Exception as e:
        return {
            "success": False,
            "message": "Error retrieving timeline entries.",
            "details": None,
            "errors": [str(e)]
        }
    
    if len(new_entries) == 0:
        return {
            "success": True,
            "message": "No new entries to analyze for conditions.",
            "details": None,
            "errors": None
        }
    
    # Prepare context for condition detection LLM using current summary and new timeline entries
    try:
        current_consultation = crud.get_consultation_by_id(db, consultation_id)
        if not current_consultation:
            raise ValueError(f"Consultation {consultation_id} not found")
        
        summary_context = current_consultation.summary or "No summary available."
        # Use compressed insights where available — they're shorter and more signal-dense
        # Fall back to the raw USER/MODEL turn only if no insight was extracted yet
        new_entries_context = []
        for entry in new_entries:
            if entry.insights and entry.insights not in ("Pending End-of-Session Extraction", "No clinical insight extracted."):
                new_entries_context.append(entry.insights)
            else:
                new_entries_context.append(f"USER: {entry.user_query}\nMODEL: {entry.model_response}")
    except Exception as e:
        return {
            "success": False,
            "message": "Error preparing context for condition detection.",
            "details": None,
            "errors": [str(e)]
        }
    
    # --- LLM CALL ---
    detected_conditions = None
    try:
        # Call the condition detection LLM - Ensure it returns List[ConditionAction]
        detected_conditions: List[ConditionAction] = data_processing_llm.detect_condition(
            summary_context,
            new_entries_context,
            user_health_records_context
        )
        
        # Filter out 'ignore' modes before processing
        actionable_conditions = [c for c in detected_conditions if c.mode != 'ignore']
    
    except Exception as e:
        return {
            "success": False,
            "message": "Error during condition detection LLM call.",
            "details": None,
            "errors": [str(e)]
        }
    
    # Log new conditions to the database
    log_messages = []
    log_errors = []
    
    # Iterate over Pydantic objects, not dictionaries
    for idx, condition in enumerate(actionable_conditions):
        if condition.mode == 'add':
            try:
                # Access attributes using dot notation (.condition_name, .condition_type)
                embedding_vector = embedder.generate_embedding_for_condition(condition)
                
                crud.add_user_condition(
                    db,
                    condition_name=condition.condition_name,
                    condition_type=condition.condition_type,
                    source_type="consultation",
                    consultation_id=consultation_id,
                    user_id=current_consultation.user_id,
                    diagnosis_date=func.now(),
                    is_active=condition.is_active,  # Access directly from Pydantic object
                    notes=condition.notes,
                    embedding_vector=embedding_vector
                )
                log_messages.append(f"Added: {condition.condition_name}")
            except Exception as e:
                log_errors.append(f"Error adding {condition.condition_name}: {str(e)}")
        
        elif condition.mode == 'update':
            try:
                # Use condition.condition_id, which is Optional[int]
                existing_condition = crud.get_condition_by_id(db, condition.condition_id)
                
                if existing_condition:
                    crud.update_user_condition(
                        db,
                        condition_id=condition.condition_id,
                        new_status=condition.is_active,
                        notes=condition.notes
                    )
                    log_messages.append(f"Updated: {condition.condition_name} (ID: {condition.condition_id})")
                else:
                    # The model used a placeholder ID — this condition doesn't exist yet.
                    # Fall back to adding it as a new condition instead.
                    print(f"[INFO] Condition ID {condition.condition_id} not found, adding as new condition: {condition.condition_name}")
                    embedding_vector = embedder.generate_embedding_for_condition(condition)
                    crud.add_user_condition(
                        db,
                        condition_name=condition.condition_name,
                        condition_type=condition.condition_type,
                        source_type="consultation",
                        consultation_id=consultation_id,
                        user_id=current_consultation.user_id,
                        diagnosis_date=func.now(),
                        is_active=condition.is_active,
                        notes=condition.notes,
                        embedding_vector=embedding_vector
                    )
                    log_messages.append(f"Added (from update fallback): {condition.condition_name}")
            except Exception as e:
                log_errors.append(f"Error processing condition ID {condition.condition_id}: {str(e)}")
    
    # Update the last condition check time
    try:
        crud.update_last_condition_check_time(db, consultation_id)
        log_messages.append("Condition check time updated.")
    except Exception as e:
        log_errors.append(f"Error updating last condition check time: {str(e)}")
    
    # Return consistent format
    if log_errors:
        return {
            "success": False,
            "message": "Processing complete with errors.",
            "details": log_messages if log_messages else None,
            "errors": log_errors
        }
    else:
        return {
            "success": True,
            "message": "Successfully processed all detected conditions.",
            "details": log_messages,
            "errors": None
        }

