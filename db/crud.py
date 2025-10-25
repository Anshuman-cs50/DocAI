from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import Date, func, text, DateTime, union_all
from db import models


# -------------------- USER FUNCTIONS --------------------

def create_user(db: Session, name: str, email: str):
    user = models.User(name=name, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


# -------------------- CONSULTATION FUNCTIONS --------------------

def create_consultation(db: Session, user_id: int, heading: str, reference: int = None):
    # Ensure reference is int as per FK, not str as in old function signature 
    consultation = models.Consultation(user_id=user_id, heading=heading, reference=reference)
    db.add(consultation)
    db.commit()
    db.refresh(consultation)
    return consultation

def get_recent_consultations(db: Session, user_id: int, limit: int = 5):
    return (db.query(models.Consultation)
              .filter(models.Consultation.user_id == user_id)
              .order_by(models.Consultation.updated_at.desc())
              .limit(limit)
              .all())

def get_consultation_by_id(db: Session, consultation_id: int):
    return db.query(models.Consultation).filter(models.Consultation.id == consultation_id).first()


def get_unsummarized_timeline_entries(db: Session, consultation_id: int, limit: int = 10):
    """
    Retrieves timeline entries for a consultation that were created *after* the consultation's last updated_at timestamp.
    """
    consultation = db.query(models.Consultation.updated_at).filter(
        models.Consultation.id == consultation_id
    ).first()

    if not consultation:
        return []

    last_update_time = consultation.updated_at

    return (db.query(models.ConsultationTimeline)
            .filter(
                models.ConsultationTimeline.consultation_id == consultation_id,
                # Filter for entries created AFTER the last summary update
                models.ConsultationTimeline.created_at > last_update_time
            )
            .order_by(models.ConsultationTimeline.created_at.asc())
            .limit(limit)
            .all())


def update_consultation_summary_and_embedding(
    db: Session,
    consultation_id: int,
    new_summary: str,
    new_embedding_vector: Optional[List[float]]
) -> None:
    """
    Updates the consultation summary, its vector embedding, and triggers the
    updated_at timestamp to reflect the new summary.
    """
    consultation = db.query(models.Consultation).filter(models.Consultation.id == consultation_id).first()
    
    if consultation:
        consultation.summary = new_summary
        consultation.embedding_vector = new_embedding_vector
        # updated_at will automatically update due to onupdate=datetime.utcnow in the model
        db.commit()
        db.refresh(consultation)

    # return consultation

# -------------------- TIMELINE FUNCTIONS --------------------

def add_timeline_entry(db: Session, consultation_id: int, user_query: str, model_response: str, insights: str = None, embedding_vector=None):
    # 🛠 MODIFIED: Changed argument name 'embedding' to 'embedding_vector'
    entry = models.ConsultationTimeline(
        consultation_id=consultation_id,
        user_query=user_query,
        model_response=model_response,
        insights=insights,
        embedding_vector=embedding_vector # Ensure this matches model column
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def get_recent_timeline_entries(db: Session, consultation_id: int, limit: int = 5):
    return (db.query(models.ConsultationTimeline)
              .filter(models.ConsultationTimeline.consultation_id == consultation_id)
              .order_by(models.ConsultationTimeline.created_at.desc())  # from latest to oldest
              .limit(limit)
              .all())

def get_all_timeline_entries(db: Session, consultation_id: int):
    return (db.query(models.ConsultationTimeline)
              .filter(models.ConsultationTimeline.consultation_id == consultation_id)
              .order_by(models.ConsultationTimeline.created_at.asc())   # from oldest to latest
              .all())


# -------------------- USER CONDITION FUNCTIONS --------------------

def add_user_condition(
    db: Session,
    user_id: int,
    condition_name: str,
    condition_type: str,
    source_type: str,
    diagnosis_date: Date = None,
    is_active: bool = True,
    notes: str = "",
    embedding_vector=None,
    consultation_id: int = None,
):
    """Creates a new record for a user's permanent/chronic health condition."""
    condition = models.UserCondition(
        user_id=user_id,
        condition_name=condition_name,
        condition_type=condition_type,
        source_type=source_type,
        diagnosis_date=diagnosis_date,
        is_active=is_active,
        notes=notes,
        embedding_vector=embedding_vector,
        consultation_id=consultation_id,
    )
    db.add(condition)
    db.commit()
    db.refresh(condition)
    return condition


# NOTE: right now there is no implementation for this function in the logic
# NOTE: later when we write code for the user to access his conditions then this function will be useful
def get_user_conditions(db: Session, user_id: int, is_active: bool = None):
    """Retrieves all (or active/inactive) permanent conditions for a user."""
    query = db.query(models.UserCondition).filter(models.UserCondition.user_id == user_id)
    if is_active is not None:
        query = query.filter(models.UserCondition.is_active == is_active)
    
    # Order by condition type and then active status for clarity
    return query.order_by(models.UserCondition.condition_type.asc(), models.UserCondition.is_active.desc()).all()


# NOTE: 
def update_condition_status(db: Session, condition_id: int, new_status: bool):
    """Updates the active status of a permanent condition (e.g., condition resolved)."""
    condition = db.query(models.UserCondition).filter(models.UserCondition.id == condition_id).first()
    if condition:
        condition.is_active = new_status
        db.commit()
        db.refresh(condition)
    return condition


# NOTE:
def delete_user_condition(db: Session, condition_id: int):
    """Deletes a permanent condition record."""
    condition = db.query(models.UserCondition).filter(models.UserCondition.id == condition_id).first()
    if condition:
        db.delete(condition)
        db.commit()
        return True
    return False


# -------------------- VITALS TIME SERIES FUNCTIONS --------------------

def add_vitals_entry(
    db: Session,
    user_id: int,
    metric_name: str,
    metric_value: float,
    timestamp: DateTime = None,
    consultation_id: int = None,
):
    """Adds a single measurement point (e.g., heart rate at a specific time) for a user."""
    if timestamp is None:
        timestamp = func.now()
        
    vitals_entry = models.VitalsTimeSeries(
        user_id=user_id,
        metric_name=metric_name,
        metric_value=metric_value,
        timestamp=timestamp,
        consultation_id=consultation_id,
    )
    db.add(vitals_entry)
    db.commit()
    db.refresh(vitals_entry)
    return vitals_entry


def get_vitals_by_range(
    db: Session,
    user_id: int,
    metric_name: str,
    start_time: DateTime,
    end_time: DateTime,
):
    """Retrieves a specific vital sign's readings for a user within a time range."""
    return (db.query(models.VitalsTimeSeries)
            .filter(
                models.VitalsTimeSeries.user_id == user_id,
                models.VitalsTimeSeries.metric_name == metric_name,
                models.VitalsTimeSeries.timestamp >= start_time,
                models.VitalsTimeSeries.timestamp <= end_time,
            )
            .order_by(models.VitalsTimeSeries.timestamp.asc())
            .all())


def get_latest_vitals(db: Session, user_id: int):
    """Retrieves the single latest reading for *each* metric for a user."""
    # This query uses an advanced window function or GROUP BY in pure SQL for efficiency
    # For simplicity and cross-DB compatibility in SQLAlchemy, we'll use a subquery/filtering approach:
    
    # This is often best handled by an optimized pure-SQL query, but here's a working SQLAlchemy approach:
    subquery = (db.query(
        models.VitalsTimeSeries.metric_name,
        func.max(models.VitalsTimeSeries.timestamp).label("max_timestamp")
    )
    .filter(models.VitalsTimeSeries.user_id == user_id)
    .group_by(models.VitalsTimeSeries.metric_name)
    .subquery())

    return (db.query(models.VitalsTimeSeries)
            .join(subquery, 
                  models.VitalsTimeSeries.metric_name == subquery.c.metric_name)
            .filter(
                models.VitalsTimeSeries.user_id == user_id,
                models.VitalsTimeSeries.timestamp == subquery.c.max_timestamp
            )
            .all())


# -------------------- VECTOR SEARCH FUNCTION --------------------

def semantic_search_records(
    db: Session, 
    user_id: int, 
    query_embedding, 
    current_consultation_id: int = None, # 🛠 NEW: Parameter to exclude the current consultation
    k_consultations: int = 2,            # 🛠 NEW: Limit for consultations
    k_conditions: int = 5                # Limit for permanent conditions
):
    """
    Performs semantic search across UserCondition notes and Consultation summaries 
    for relevant health context, excluding the current consultation.
    """
    
    # 1. Search User Permanent Conditions
    # We retrieve more conditions (k_conditions) as they are highly relevant and static.
    condition_results = (
        db.query(
            models.UserCondition.notes.label("text_snippet"),
            models.UserCondition.condition_name.label("title"),
            models.UserCondition.diagnosis_date.label("date"),
            text("'User Condition'").label("type"),
            (models.UserCondition.embedding_vector.op('<=>')(query_embedding)).label("distance")
        )
        .filter(models.UserCondition.user_id == user_id)
        .order_by(text("distance"))
        .limit(k_conditions)
    ).subquery("conditions")

    # 2. Search Consultation Summaries
    consultation_query = (
        db.query(
            models.Consultation.summary.label("text_snippet"),
            models.Consultation.heading.label("title"),
            models.Consultation.created_at.label("date"),
            text("'Consultation Summary'").label("type"),
            (models.Consultation.embedding_vector.op('<=>')(query_embedding)).label("distance")
        )
        .filter(models.Consultation.user_id == user_id)
    )
    
    # 🛠 IMPLEMENTATION: Logic to exclude the current consultation
    if current_consultation_id is not None:
        consultation_query = consultation_query.filter(
            models.Consultation.id != current_consultation_id
        )

    consultation_results = (
        consultation_query
        .order_by(text("distance"))
        .limit(k_consultations) # Limit consultation results to 2
    ).subquery("consultations")
    
    # 3. Combine and Final Sort
    # Use union_all to combine the results from the two subqueries
    combined_query = union_all(
        db.query(condition_results).subquery().select(),
        db.query(consultation_results).subquery().select()
    ).alias("combined_records")

    # Retrieve all combined results, sorted by distance for overall relevancy
    final_results = (
        db.query(combined_query)
        .order_by(combined_query.c.distance.asc())
        .all()
    )
    
    # Convert results to a list of dictionaries for easier AI consumption
    return [
        {
            "type": r.type,
            "title": r.title,
            "snippet": r.text_snippet,
            "date": r.date.isoformat() if r.date else None, # Format date for clean output
            "relevance_distance": r.distance
        }
        for r in final_results
    ]