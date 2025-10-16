# app/routes.py
from flask import Blueprint, jsonify, request
from db.database import SessionLocal
from db import crud

main = Blueprint("main", __name__)

@main.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Server running!"})

@main.route("/test_create_user", methods=["POST"])
def test_create_user():
    db = SessionLocal()
    data = request.get_json()
    user = crud.create_user(db, name=data["name"], email=data["email"])
    db.close()
    return jsonify({
        "message": "User created successfully!",
        "user_id": user.id,
        "name": user.name,
        "email": user.email
    })

@main.route("/test_create_consultation", methods=["POST"])
def test_create_consultation():
    db = SessionLocal()
    data = request.get_json()
    consultation = crud.create_consultation(
        db, user_id=data["user_id"], heading=data["heading"]
    )
    db.close()
    return jsonify({
        "message": "Consultation created!",
        "consultation_id": consultation.id,
        "heading": consultation.heading
    })

@main.route("/test_add_timeline", methods=["POST"])
def test_add_timeline():
    db = SessionLocal()
    data = request.get_json()
    entry = crud.add_timeline_entry(
        db,
        consultation_id=data["consultation_id"],
        user_query=data["user_query"],
        model_response=data["model_response"],
        insights=data.get("insights", "")
    )
    db.close()
    return jsonify({
        "message": "Timeline entry added!",
        "entry_id": entry.id,
        "consultation_id": entry.consultation_id
    })

@main.route("/test_recent_consultations/<int:user_id>", methods=["GET"])
def test_recent_consultations(user_id):
    db = SessionLocal()
    consultations = crud.get_recent_consultations(db, user_id=user_id)
    db.close()
    return jsonify([
        {"id": c.id, "heading": c.heading, "summary": c.summary}
        for c in consultations
    ])

@main.route("/test_timeline/<int:consultation_id>", methods=["GET"])
def test_timeline(consultation_id):
    db = SessionLocal()
    timeline = crud.get_timeline_for_consultation(db, consultation_id=consultation_id)
    db.close()
    return jsonify([
        {
            "id": entry.id,
            "user_query": entry.user_query,
            "model_response": entry.model_response,
            "insights": entry.insights,
            "created_at": entry.created_at.isoformat()
        }
        for entry in timeline
    ])
