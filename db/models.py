# db/models.py
from sqlalchemy import Column, Integer, Numeric, String, ForeignKey, Text, DateTime, Date, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base
from pgvector.sqlalchemy import Vector


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    consultations = relationship("Consultation", back_populates="user", cascade="all, delete-orphan")


class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    heading = Column(Text, default="")
    reference = Column(Integer, ForeignKey("consultations.id"), nullable=True)
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)  
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    user = relationship("User", back_populates="consultations")
    referenced_consultation = relationship("Consultation", remote_side=[id], backref="referencing_consultations", uselist=False)
    timeline_entries = relationship("ConsultationTimeline", back_populates="consultation", cascade="all, delete-orphan")


class ConsultationTimeline(Base):
    __tablename__ = "consultation_timeline"

    id = Column(Integer, primary_key=True, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"))
    user_query = Column(Text)
    model_response = Column(Text)
    insights = Column(Text, nullable=True)
    embedding_vector = Column(Vector(1536)) # adjust according to the embedding model
    created_at = Column(DateTime, default=datetime.utcnow)

    consultation = relationship("Consultation", back_populates="timeline_entries")

class UserCondition(Base):
    __tablename__ = "user_conditions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Core Link to User
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    
    # Source Separation (Improved from 'source_of_information')
    source_type = Column(String(50), nullable=False) # e.g., 'Consultation', 'User_Report', 'Lab_Result'
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=True) # Only populated if source_type is 'Consultation'
    
    # Categorization (Improved from 'category_onset')
    condition_type = Column(String(100), nullable=False, index=True) # e.g., 'Chronic_Disease', 'Allergy', 'Acute_Infection'
    condition_name = Column(String(255), nullable=False)            # e.g., 'Hypertension', 'Seasonal Rhinitis'
    
    # Status and Temporal Data
    diagnosis_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, index=True) 
    
    # Contextual and Search Data
    notes = Column(Text, default="")
    embedding_vector = Column(Vector(1536), nullable=True) 

    # Audit Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    consultation = relationship("Consultation")


class VitalsTimeSeries(Base):
    __tablename__ = "vitals_time_series"

    id = Column(Integer, primary_key=True, index=True)
    
    # Core Link to User
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    
    # The essential time component for TimescaleDB optimization and time-series queries
    timestamp = Column(DateTime, default=func.now(), index=True) 
    
    # Identifier for the metric being recorded (e.g., 'heart_rate', 'bp_systolic', 'spo2')
    metric_name = Column(String(50), nullable=False)
    
    # The actual numerical measurement (e.g., 72, 120.5, 98)
    # Using Numeric for high precision required for medical readings
    metric_value = Column(Numeric(10, 2), nullable=False)
    
    # Optional: Link to a specific consultation if the reading was taken during it
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=True)

    # Relationships (Optional, but good practice)
    user = relationship("User")
    consultation = relationship("Consultation")

