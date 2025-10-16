# db/crud.py
from sqlalchemy.orm import Session
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

def create_consultation(db: Session, user_id: int, heading: str, reference: str = None):
    consultation = models.Consultation(user_id=user_id, heading=heading, reference=reference)
    db.add(consultation)
    db.commit()
    db.refresh(consultation)
    return consultation

def update_consultation_summary(db: Session, consultation_id: int, new_summary: str):
    consultation = db.query(models.Consultation).filter(models.Consultation.id == consultation_id).first()
    if consultation:
        consultation.summary = new_summary
        db.commit()
        db.refresh(consultation)
    return consultation

def get_recent_consultations(db: Session, user_id: int, limit: int = 5):
    return (db.query(models.Consultation)
              .filter(models.Consultation.user_id == user_id)
              .order_by(models.Consultation.updated_at.desc())
              .limit(limit)
              .all())

def get_timeline_for_consultation(db: Session, consultation_id: int):
    return (db.query(models.ConsultationTimeline)
              .filter(models.ConsultationTimeline.consultation_id == consultation_id)
              .order_by(models.ConsultationTimeline.created_at.asc())
              .all())


# -------------------- TIMELINE FUNCTIONS --------------------

def add_timeline_entry(db: Session, consultation_id: int, user_query: str, model_response: str, insights: str = None):
    entry = models.ConsultationTimeline(
        consultation_id=consultation_id,
        user_query=user_query,
        model_response=model_response,
        insights=insights
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def get_timeline_for_consultation(db: Session, consultation_id: int):
    return (db.query(models.ConsultationTimeline)
              .filter(models.ConsultationTimeline.consultation_id == consultation_id)
              .order_by(models.ConsultationTimeline.created_at.asc())
              .all())
