# db/models.py
from sqlalchemy import Column, Integer, Numeric, String, ForeignKey, Text, DateTime, Date, Boolean, func
from sqlalchemy.orm import relationship
from db.database import Base
from pgvector.sqlalchemy import Vector


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True)
    created_at = Column(DateTime, default=func.now()) # Use func.now() for database default

    consultations = relationship("Consultation", back_populates="user", cascade="all, delete-orphan")

    conditions = relationship("UserCondition", back_populates="user", cascade="all, delete-orphan")
    vitals = relationship("VitalsTimeSeries", back_populates="user", cascade="all, delete-orphan")


class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    heading = Column(String(255), default="") 
    reference = Column(Integer, ForeignKey("consultations.id"), nullable=True)
    summary = Column(Text, default="")
    embedding_vector = Column(Vector(1536), nullable=True)
    created_at = Column(DateTime, default=func.now())  
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Tracking the last time we ran the condition detection LLM
    last_condition_check_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="consultations")
    referenced_consultation = relationship("Consultation", remote_side=[id], backref="referencing_consultations", uselist=False)
    timeline_entries = relationship("ConsultationTimeline", back_populates="consultation", cascade="all, delete-orphan")
    
    conditions = relationship("UserCondition", back_populates="consultation")
    vitals_entries = relationship("VitalsTimeSeries", back_populates="consultation")


class ConsultationTimeline(Base):
    __tablename__ = "consultation_timeline"

    id = Column(Integer, primary_key=True, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"))
    user_query = Column(Text) 
    model_response = Column(Text)
    insights = Column(Text, nullable=True)
    embedding_vector = Column(Vector(1536))
    created_at = Column(DateTime, default=func.now()) # Use func.now() for consistency

    consultation = relationship("Consultation", back_populates="timeline_entries")


class UserCondition(Base):
    __tablename__ = "user_conditions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Core Link to User
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    
    # Source Separation
    source_type = Column(String(50), nullable=False)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=True)
    
    # Categorization
    condition_type = Column(String(100), nullable=False, index=True)
    condition_name = Column(String(255), nullable=False)
    
    # Status and Temporal Data
    diagnosis_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, index=True) 
    
    # Contextual and Search Data
    notes = Column(Text, default="")
    embedding_vector = Column(Vector(1536), nullable=True) 

    # Audit Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="conditions") 
    consultation = relationship("Consultation", back_populates="conditions")


class VitalsTimeSeries(Base):
    __tablename__ = "vitals_time_series"

    id = Column(Integer, primary_key=True, index=True)
    
    # Core Link to User
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    
    # The essential time component for TimescaleDB optimization and time-series queries
    timestamp = Column(DateTime, default=func.now(), index=True)
    
    # Identifier for the metric being recorded
    metric_name = Column(String(50), nullable=False)
    
    # The actual numerical measurement
    metric_value = Column(Numeric(10, 2), nullable=False)
    
    # Optional: Link to a specific consultation
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=True)

    user = relationship("User", back_populates="vitals_entries") 
    consultation = relationship("Consultation", back_populates="vitals_entries")