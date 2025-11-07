from sqlalchemy.orm import Session
from sqlalchemy import func
from db import crud
import embedding
from flask import jsonify
from ai import embedding, LLM_module
from typing import List
from ai.LLM_module import ConditionAction

data_processing_llm = LLM_module.DataProcessingLLM()
embedder = embedding.MedicalEmbedder()

# define the threshold for condition checking
CONDITION_CHECK_THRESHOLD = 5

def check_and_log_user_conditions(
    db: Session,
    consultation_id: int,
    user_health_records_context: str
):
    """
    Checks for new user conditions based on the last condition check time
    """

    # get the last condition check time
    last_check_time = crud.get_last_condition_check_time(db, consultation_id)
    if last_check_time is None:
        return jsonify({"error": "Consultation not found."})
    
    # check if enough timeline entries have been added since last check
    new_entries = crud.get_timeline_entries_since(
        db,
        consultation_id,
        since=last_check_time
    )

    if len(new_entries) < CONDITION_CHECK_THRESHOLD:
        return jsonify({"message": "No new conditions to log at this time.", "status_code": 1})
    
    # Prepare context for condition detection LLM using current summary and new timeline entries
    current_consultation = crud.get_consultation_by_id(db, consultation_id)
    summary_context = current_consultation.summary or "No summary available."
    new_entries_context = [entry.model_response for entry in new_entries]

    # --- LLM CALL ---
    try:
        # Call the condition detection LLM - Ensure it returns List[ConditionAction]
        detected_conditions: List[ConditionAction] = data_processing_llm.detect_conditions(
            summary_context, 
            new_entries_context, 
            user_health_records_context
        )
        # Filter out 'ignore' modes before processing
        actionable_conditions = [c for c in detected_conditions if c.mode != 'ignore']

    except Exception as e:
        return jsonify({"error": f"error during condition detection LLM call:\n {str(e)}"})
    
    # Log new conditions to the database
    log_messages = []
    log_errors = []

    # Iterate over Pydantic objects, not dictionaries
    for condition in actionable_conditions:
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
                    is_active=condition.is_active, # Access directly from Pydantic object
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
                    # Log an error if the model proposed an update for a non-existent ID
                    log_errors.append(f"Update failed: Condition ID {condition.condition_id} not found.")
            except Exception as e:
                log_errors.append(f"Error updating condition ID {condition.condition_id}: {str(e)}")


    # Update the last condition check time
    try:
        crud.update_last_condition_check_time(
            db,
            consultation_id,
            new_check_time=func.now()
        )
        log_messages.append("Condition check time updated.")
    except Exception as e:
        log_errors.append(f"Error updating last condition check time: {str(e)}")

    # Combine messages and return the final response
    if log_errors:
        return jsonify({"message": "Processing complete with errors.", "details": log_messages, "errors": log_errors, "status_code": 5})
    else:
        return jsonify({"message": "Successfully processed all detected conditions.", "details": log_messages, "status_code": 3})