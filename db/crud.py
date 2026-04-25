from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import Date, func, literal, select, text, DateTime, union_all, literal_column, bindparam, cast
from pgvector.sqlalchemy import Vector
from pgvector import Vector as PgVector
import numpy as np
from . import models
from .models import VECTOR_DIMENSION

SIMILARITY_THRESHOLD = 0.4
# Safety ceiling — prevents token overflow on very large patient histories.
# The real filter is the similarity threshold; this is just a hard backstop.
MAX_FINAL_CONTEXT_CHUNKS = 15


# -------------------- USER FUNCTIONS --------------------

def create_user(
    db: Session, 
    name: str, 
    email: str, 
    password_hash: str = None, 
    age: int = None, 
    gender: str = None,
    blood_type: str = None,
    height_cm: float = None,
    weight_kg: float = None,
    pre_existing_conditions: List[str] = None
):
    user = models.User(
        name=name, 
        email=email, 
        password_hash=password_hash,
        age=age,
        gender=gender,
        blood_type=blood_type,
        height_cm=height_cm,
        weight_kg=weight_kg
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    if pre_existing_conditions:
        for cond_name in pre_existing_conditions:
            if cond_name.strip():
                condition = models.UserCondition(
                    user_id=user.id,
                    source_type="signup_form",
                    condition_type="condition",
                    condition_name=cond_name.strip(),
                    is_active=True,
                    notes="Reported by patient during signup"
                )
                db.add(condition)
        db.commit()
        
    return user

def update_user_profile(
    db: Session, 
    user_id: int, 
    age: int = None, 
    gender: str = None,
    blood_type: str = None,
    height_cm: float = None,
    weight_kg: float = None
):
    user = get_user_by_id(db, user_id)
    if not user:
        return None
        
    if age is not None:
        user.age = age
    if gender is not None:
        user.gender = gender
    if blood_type is not None:
        user.blood_type = blood_type
    if height_cm is not None:
        user.height_cm = height_cm
    if weight_kg is not None:
        user.weight_kg = weight_kg
        
    db.commit()
    db.refresh(user)
    return user

def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


# -------------------- CONSULTATION FUNCTIONS --------------------

def resolve_user_condition(db: Session, user_id: int, condition_name: str):
    condition = db.query(models.UserCondition).filter(
        models.UserCondition.user_id == user_id,
        models.UserCondition.condition_name == condition_name,
        models.UserCondition.is_active == True
    ).first()
    
    if condition:
        condition.is_active = False
        db.commit()
        db.refresh(condition)
        return True
    return False

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

def end_consultation(db: Session, consultation_id: int):
    consultation = db.query(models.Consultation).filter(models.Consultation.id == consultation_id).first()
    if consultation:
        consultation.is_active = False
        db.commit()
        db.refresh(consultation)
    return consultation


def get_unsummarized_timeline_entries(db: Session, consultation_id: int, limit: int = 50):
    """
    Retrieves timeline entries for a consultation that have not been summarized yet.
    """
    return (db.query(models.ConsultationTimeline)
            .filter(
                models.ConsultationTimeline.consultation_id == consultation_id,
                # Filter for entries that are pending extraction
                models.ConsultationTimeline.insights.in_([None, "", "Pending End-of-Session Extraction"])
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
        # Convert NumPy array to list for pgvector compatibility
        if new_embedding_vector is not None:
            if isinstance(new_embedding_vector, np.ndarray):
                new_embedding_vector = new_embedding_vector.tolist()
        consultation.embedding_vector = new_embedding_vector
        # updated_at will automatically update due to onupdate=datetime.utcnow in the model
        db.commit()
        db.refresh(consultation)


def get_last_condition_check_time(db: Session, consultation_id: int):
    consultation = db.query(models.Consultation).filter(models.Consultation.id == consultation_id).first()
    if consultation:
        return consultation.last_condition_check_at
    return None

def update_last_condition_check_time(db: Session, consultation_id: int):
    consultation = db.query(models.Consultation).filter(models.Consultation.id == consultation_id).first()
    if consultation:
        consultation.last_condition_check_at = func.now()
        db.commit()
        db.refresh(consultation)


# -------------------- TIMELINE FUNCTIONS --------------------

def add_timeline_entry(db: Session, consultation_id: int, user_query: str, model_response: str, insights: str = None, embedding_vector=None):
    # 🛠 MODIFIED: Changed argument name 'embedding' to 'embedding_vector'
    # Convert NumPy array to list for pgvector compatibility
    if embedding_vector is not None:
        if isinstance(embedding_vector, np.ndarray):
            embedding_vector = embedding_vector.tolist()
    
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
    entries = (db.query(models.ConsultationTimeline)
              .filter(models.ConsultationTimeline.consultation_id == consultation_id)
              .order_by(models.ConsultationTimeline.created_at.desc())  # get latest first
              .limit(limit)
              .all())
    return entries[::-1]  # reverse to restore chronological order (oldest to newest)

def get_all_timeline_entries(db: Session, consultation_id: int):
    return (db.query(models.ConsultationTimeline)
              .filter(models.ConsultationTimeline.consultation_id == consultation_id)
              .order_by(models.ConsultationTimeline.created_at.asc())   # from oldest to latest
              .all())

def get_timeline_entries_since(db: Session, consultation_id: int, since: DateTime):
    """Retrieves timeline entries for a consultation created after a specific timestamp."""
    return (db.query(models.ConsultationTimeline)
            .filter(
                models.ConsultationTimeline.consultation_id == consultation_id,
                models.ConsultationTimeline.created_at > since
            )
            .order_by(models.ConsultationTimeline.created_at.asc())
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
    # Convert NumPy array to list for pgvector compatibility
    if embedding_vector is not None:
        if isinstance(embedding_vector, np.ndarray):
            embedding_vector = embedding_vector.tolist()
    
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

def get_condition_by_id(db: Session, condition_id: int):
    """Retrieves a user condition by its ID."""
    return db.query(models.UserCondition).filter(models.UserCondition.id == condition_id).first()


def update_user_condition(
    db: Session,
    condition_id: int,
    new_status: bool,
    notes: str = None
):
    """Updates a user's condition record."""
    condition = db.query(models.UserCondition).filter(models.UserCondition.id == condition_id).first()
    if condition:
        condition.is_active = new_status
        if notes is not None:
            condition.notes = notes
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

# Assuming models are imported correctly (e.g., models.UserCondition, models.Consultation)
# Assuming SIMILARITY_THRESHOLD is defined globally or passed in

# --- Define the Calibrated Parameters ---
# Based on the Gradient Test, 0.50 is the boundary for "Less Semi-Similar" context.
# We set the Distance Threshold (1 - Similarity) to 0.50.
# We set the maximum number of final results (Top-N) to 4.

def semantic_search_records(
    db: Session, 
    user_id: int, 
    query_embedding, # MUST be a 1D NumPy array/list
    current_consultation_id: int = None,
    k_consultations: int = 20,
    k_conditions: int = 20,
    SIMILARITY_THRESHOLD_VALUE: float = SIMILARITY_THRESHOLD,
    MAX_FINAL_CONTEXT_CHUNKS: int = MAX_FINAL_CONTEXT_CHUNKS
):
    """ 
    Performs semantic search across UserCondition notes and Consultation summaries 
    with a hybrid distance/similarity threshold and a final Top-N limit.
    
    Uses raw SQL to bypass SQLAlchemy's type processors which cause ndim errors.
    """
    
    # 1. CALCULATE THE DISTANCE THRESHOLD
    DISTANCE_THRESHOLD = 1.0 - SIMILARITY_THRESHOLD_VALUE
    
    # 2. Convert embedding to list format that PostgreSQL can handle
    if isinstance(query_embedding, list):
        query_embedding = np.array(query_embedding, dtype=np.float32)
    elif not isinstance(query_embedding, np.ndarray):
        query_embedding = np.array(query_embedding, dtype=np.float32)
    
    # Ensure it's 1D
    if query_embedding.ndim != 1:
        query_embedding = query_embedding.flatten()
    
    # Convert to list of floats - PostgreSQL will handle the Vector conversion via CAST
    query_embedding_list = [float(x) for x in query_embedding.tolist()]
    
    # 3. Build raw SQL query to bypass SQLAlchemy's type processors
    # We use PostgreSQL's native parameter binding with :param_name syntax
    current_consultation_filter = ""
    if current_consultation_id is not None:
        current_consultation_filter = f"AND consultations.id != {current_consultation_id}"
    
    sql_query = text(f"""
        WITH condition_results AS (
            SELECT 
                user_conditions.notes AS text_snippet,
                user_conditions.condition_name AS title,
                user_conditions.diagnosis_date AS date,
                'User Condition' AS type,
                user_conditions.embedding_vector <=> CAST(:query_vec AS vector({VECTOR_DIMENSION})) AS distance,
                1.0 - (user_conditions.embedding_vector <=> CAST(:query_vec AS vector({VECTOR_DIMENSION}))) AS similarity_score
            FROM user_conditions
            WHERE user_conditions.user_id = :user_id
                AND (user_conditions.embedding_vector <=> CAST(:query_vec AS vector({VECTOR_DIMENSION}))) <= :distance_threshold
            ORDER BY user_conditions.embedding_vector <=> CAST(:query_vec AS vector({VECTOR_DIMENSION}))
            LIMIT :k_conditions
        ),
        consultation_results AS (
            SELECT 
                consultations.summary AS text_snippet,
                consultations.heading AS title,
                consultations.created_at AS date,
                'Consultation Summary' AS type,
                consultations.embedding_vector <=> CAST(:query_vec AS vector({VECTOR_DIMENSION})) AS distance,
                1.0 - (consultations.embedding_vector <=> CAST(:query_vec AS vector({VECTOR_DIMENSION}))) AS similarity_score
            FROM consultations
            WHERE consultations.user_id = :user_id
                {current_consultation_filter}
                AND (consultations.embedding_vector <=> CAST(:query_vec AS vector({VECTOR_DIMENSION}))) <= :distance_threshold
            ORDER BY consultations.embedding_vector <=> CAST(:query_vec AS vector({VECTOR_DIMENSION}))
            LIMIT :k_consultations
        ),
        timeline_ranked AS (
            SELECT 
                timeline.insights AS text_snippet,
                consultations.heading AS title,
                timeline.created_at AS date,
                'Clinical Insight' AS type,
                timeline.embedding_vector <=> CAST(:query_vec AS vector({VECTOR_DIMENSION})) AS distance,
                1.0 - (timeline.embedding_vector <=> CAST(:query_vec AS vector({VECTOR_DIMENSION}))) AS similarity_score,
                ROW_NUMBER() OVER (
                    PARTITION BY timeline.consultation_id
                    ORDER BY timeline.embedding_vector <=> CAST(:query_vec AS vector({VECTOR_DIMENSION})) ASC
                ) AS rn
            FROM consultation_timeline timeline
            JOIN consultations ON consultations.id = timeline.consultation_id
            WHERE consultations.user_id = :user_id
                {current_consultation_filter.replace('consultations.id', 'timeline.consultation_id')}
                AND timeline.embedding_vector IS NOT NULL
                AND timeline.insights IS NOT NULL
                AND timeline.insights NOT IN ('No clinical insight extracted.', 'Pending End-of-Session Extraction')
                AND (timeline.embedding_vector <=> CAST(:query_vec AS vector({VECTOR_DIMENSION}))) <= :distance_threshold
        ),
        timeline_results AS (
            SELECT text_snippet, title, date, type, distance, similarity_score
            FROM timeline_ranked
            WHERE rn = 1
            ORDER BY distance ASC
            LIMIT :k_consultations
        ),
        combined_records AS (
            SELECT * FROM condition_results
            UNION ALL
            SELECT * FROM consultation_results
            UNION ALL
            SELECT * FROM timeline_results
        )
        SELECT 
            text_snippet,
            title,
            date,
            type,
            distance,
            similarity_score
        FROM combined_records
        -- Sort by relevance so the model sees the strongest signal first.
        -- Dates are serialised per-record so the model can still reason chronologically.
        ORDER BY distance ASC
        LIMIT :max_results
    """)
    
    # 4. Execute with proper parameter binding
    # Pass the list - PostgreSQL's CAST will convert it to Vector type
    # We format it as a string representation that PostgreSQL understands: '[1.0, 2.0, ...]'
    query_vec_str = '[' + ','.join(str(x) for x in query_embedding_list) + ']'
    
    result = db.execute(
        sql_query,
        {
            'query_vec': query_vec_str,
            'user_id': user_id,
            'distance_threshold': DISTANCE_THRESHOLD,
            'k_conditions': k_conditions,
            'k_consultations': k_consultations,
            'max_results': MAX_FINAL_CONTEXT_CHUNKS
        }
    )
    
    # 5. Convert results to list of dictionaries
    final_results = result.all()
    
    return [
        {
            "type": r.type,
            "title": r.title,
            "snippet": r.text_snippet,
            "date": r.date.isoformat() if r.date else None,
            "relevance_distance": float(r.distance),
            "relevance_similarity": float(r.similarity_score)
        }
        for r in final_results
    ]