import traceback
import json
import numpy as np
from sqlalchemy import func
from db import crud, models
from db.database import SessionLocal
from ai import ai as ai_module
from ai.LLM_module import DataProcessingLLM
from ai.embedding import MedicalEmbedder

data_processing_llm = DataProcessingLLM()
embedder = MedicalEmbedder()

def _condition_to_embed_dict(condition):
    """Convert a ConditionAction Pydantic object to the dict format MedicalEmbedder expects."""
    return {
        "name": condition.condition_name,
        "type": condition.condition_type,
        "notes": condition.notes or ""
    }

def run_end_of_session_pipeline(consultation_id: int):
    """
    Background pipeline to process a consultation once it ends.
    - Extracts insights for unsummarized entries.
    - Summarises the consultation.
    - Detects and logs conditions.
    """
    print(f"\n[POST_PROCESSING] Starting pipeline for Consultation {consultation_id}...")
    db = SessionLocal()
    try:
        consultation = crud.get_consultation_by_id(db, consultation_id)
        if not consultation:
            print(f"[POST_PROCESSING] Consultation {consultation_id} not found.")
            return

        # 1. Fetch unsummarized timeline entries
        unsummarized = crud.get_unsummarized_timeline_entries(db, consultation_id, limit=50)
        print(f"[POST_PROCESSING] Found {len(unsummarized)} unsummarized entries.")

        if len(unsummarized) == 0:
            print("[POST_PROCESSING] Nothing to process. Exiting.")
            return

        # 2. Extract Insights for each entry
        for entry in unsummarized:
            print(f"[POST_PROCESSING] Extracting insight for entry {entry.id}")
            try:
                insights_obj = ai_module.extract_insights(entry.user_query, entry.model_response)
                if insights_obj.insight_found:
                    entry.insights = insights_obj.compressed_summary
                    embedding_vector = embedder.generate_embedding(insights_obj.compressed_summary)
                    if isinstance(embedding_vector, np.ndarray):
                        embedding_vector = embedding_vector.tolist()
                    entry.embedding_vector = embedding_vector
                else:
                    entry.insights = "No clinical insight extracted."
            except Exception as e:
                print(f"[POST_PROCESSING] Insight extraction failed for entry {entry.id}: {e}")
                entry.insights = "No clinical insight extracted."
            db.commit()

        # 3. Summarization
        print("[POST_PROCESSING] Generating updated cumulative summary...")
        formatted_timeline = ""
        for entry in unsummarized:
            formatted_timeline += f"USER: {entry.user_query}\nMODEL: {entry.model_response}\n\n"

        existing_summary = consultation.summary or ""
        try:
            heading, new_summary = data_processing_llm.summarise(existing_summary, formatted_timeline)
        except Exception as e:
            print(f"[POST_PROCESSING] Summarization failed: {e}. Keeping existing summary.")
            heading, new_summary = None, existing_summary

        new_embedding = embedder.generate_embedding(new_summary)
        if isinstance(new_embedding, np.ndarray):
            new_embedding = new_embedding.tolist()

        crud.update_consultation_summary_and_embedding(db, consultation_id, new_summary, new_embedding)

        # Save the generated heading if we got one and current heading is still the default
        if heading and (not consultation.heading or consultation.heading == "New Live Consultation"):
            db_consult = crud.get_consultation_by_id(db, consultation_id)
            if db_consult:
                db_consult.heading = heading
                db.commit()
                print(f"[POST_PROCESSING] Heading updated: '{heading}'")
        
        print("[POST_PROCESSING] Summary updated.")

        # 4. Condition Detection
        print("[POST_PROCESSING] Running condition detection...")
        try:
            # Build context: prefer insights (compressed), fall back to raw turns
            new_entries_context = []
            for entry in unsummarized:
                if entry.insights and entry.insights not in ("Pending End-of-Session Extraction", "No clinical insight extracted."):
                    new_entries_context.append(entry.insights)
                else:
                    new_entries_context.append(f"USER: {entry.user_query}\nMODEL: {entry.model_response}")

            # Get existing conditions for de-duplication context
            user_conditions = db.query(models.UserCondition).filter(
                models.UserCondition.user_id == consultation.user_id
            ).all()
            user_health_records_context = [
                {"id": c.id, "name": c.condition_name, "type": c.condition_type,
                 "active": c.is_active, "notes": c.notes}
                for c in user_conditions
            ]

            # Refresh consultation for updated summary
            db.refresh(consultation)
            summary_context = consultation.summary or "No summary available."

            detected_conditions = data_processing_llm.detect_condition(
                summary_context,
                new_entries_context,
                user_health_records_context
            )

            actionable = [c for c in detected_conditions if c.mode != 'ignore']
            print(f"[POST_PROCESSING] Detected {len(actionable)} actionable condition(s).")

            for condition in actionable:
                try:
                    if condition.mode == 'add':
                        emb = embedder.generate_embedding_for_condition(_condition_to_embed_dict(condition))
                        crud.add_user_condition(
                            db,
                            condition_name=condition.condition_name,
                            condition_type=condition.condition_type,
                            source_type="consultation",
                            consultation_id=consultation_id,
                            user_id=consultation.user_id,
                            diagnosis_date=func.now(),
                            is_active=condition.is_active,
                            notes=condition.notes,
                            embedding_vector=emb
                        )
                        print(f"[POST_PROCESSING] Added condition: {condition.condition_name}")

                    elif condition.mode == 'update':
                        existing = crud.get_condition_by_id(db, condition.condition_id)
                        if existing:
                            crud.update_user_condition(db, condition.condition_id, condition.is_active, condition.notes)
                            print(f"[POST_PROCESSING] Updated condition: {condition.condition_name}")
                        else:
                            # Placeholder ID — add as new
                            emb = embedder.generate_embedding_for_condition(_condition_to_embed_dict(condition))
                            crud.add_user_condition(
                                db,
                                condition_name=condition.condition_name,
                                condition_type=condition.condition_type,
                                source_type="consultation",
                                consultation_id=consultation_id,
                                user_id=consultation.user_id,
                                diagnosis_date=func.now(),
                                is_active=condition.is_active,
                                notes=condition.notes,
                                embedding_vector=emb
                            )
                            print(f"[POST_PROCESSING] Added (from update fallback): {condition.condition_name}")

                except Exception as e:
                    print(f"[POST_PROCESSING] Error saving condition '{condition.condition_name}': {e}")
                    traceback.print_exc()

        except Exception as e:
            print(f"[POST_PROCESSING] Condition detection failed: {e}")
            traceback.print_exc()

        # 5. Mark condition check time
        crud.update_last_condition_check_time(db, consultation_id)
        print(f"[POST_PROCESSING] Pipeline for Consultation {consultation_id} completed successfully.\n")

    except Exception as e:
        print(f"[POST_PROCESSING] Error in pipeline: {e}")
        traceback.print_exc()
    finally:
        db.close()
