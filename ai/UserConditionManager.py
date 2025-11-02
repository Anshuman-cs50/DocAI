from sqlalchemy.orm import Session
from sqlalchemy import func
from db import crud
import embedding
from flask import jsonify
from ai import embedding

llm_summariser = ...
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

    condition_detection_prompt = f"""
        
    {summary_context}

    {new_entries_context}

    {user_health_records_context}
    """

    # Call the condition detection LLM
    try:
        detected_conditions = llm_summariser.detect_conditions(condition_detection_prompt)

    except Exception as e:
        return jsonify({"error": f"error during condition detection LLM call:\n {str(e)}"})
    
    # Log new conditions to the database
    log_messages = []
    log_errors = []

    for condition in detected_conditions:
        if condition['mode'] == 'add':
            try:
                embedding_vector = embedder.generate_embedding_for_condtition(condition)
                crud.add_user_condition(
                    db,
                    condition_name=condition['name'],
                    condition_type=condition['type'],
                    source_type="consultation",
                    consultation_id=consultation_id,
                    user_id=current_consultation.user_id,
                    diagnosis_date=func.now(),
                    is_active=condition.get('is_active', True),
                    notes=condition.get('notes', ""),
                    embedding_vector=embedding_vector
                )
                log_messages.append(f"Added: {condition['name']}")
            except Exception as e:
                log_errors.append(f"Error adding {condition['name']}: {str(e)}")

        elif condition['mode'] == 'update':
            try:
                existing_condition = crud.get_condition_by_id(db, condition['id'])
                if existing_condition:
                    crud.update_user_condition(
                        db,
                        condition_id=condition['id'],
                        new_status=condition.get('is_active'),
                        notes=condition.get('notes')
                    )
                    log_messages.append(f"Updated: {condition['name']}")
                else:
                    log_errors.append(f"Update failed: Condition ID {condition['id']} not found.")
            except Exception as e:
                log_errors.append(f"Error updating condition ID {condition['id']}: {str(e)}")


    # Update the last condition check time
    try:
        crud.update_last_condition_check_time(
            db,
            consultation_id,
            new_check_time=func.now()
        )
        log_messages.append("Condition check time updated.")
    except Exception as e:
        # This is a critical error but shouldn't block returning the rest of the results
        log_errors.append(f"Error updating last condition check time: {str(e)}")

    # Combine messages and return the final response
    if log_errors:
        return jsonify({"message": "Processing complete with errors.", "details": log_messages, "errors": log_errors, "status_code": 5})
    else:
        return jsonify({"message": "Successfully processed all detected conditions.", "details": log_messages, "status_code": 3})