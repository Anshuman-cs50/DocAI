# app/routes.py
from flask import Blueprint, jsonify, request
from db.database import SessionLocal
from db import crud
from ai import ai, embedding, MemoryManager as mm, UserConditionManager as ucm

embedder = embedding.MedicalEmbedder()
main = Blueprint("main", __name__)


@main.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Server running!"})


@main.route("/create_user", methods=["POST"])
def test_create_user():
    db = SessionLocal()
    data = request.get_json()

    # Basic validation
    if data["name"] is None or data["email"] is None:
        db.close()
        return jsonify({"message": "Name and email are required."}), 400
    
    # Check for existing email or user ID
    if crud.get_user_by_email(db, email=data["email"]):
        db.close()
        return jsonify({"message": "Email already registered."}), 400
    
    if crud.get_user_by_id(db, user_id=data["id"]):
        db.close()
        return jsonify({"message": "User ID already exists."}), 400
    
    # Create user
    user = crud.create_user(db, name=data["name"], email=data["email"])
    db.close()
    return jsonify({
        "message": "User created successfully!",
        "user_id": user.id,
        "name": user.name,
        "email": user.email
    })


@main.route("/create_consultation", methods=["POST"])
def test_create_consultation():
    db = SessionLocal()
    data = request.get_json()

    # Basic validation
    if data["user_id"] is None or data["heading"] is None:
        db.close()
        return jsonify({"message": "User ID and heading are required."}), 400
    
    # Check if user exists
    if not crud.get_user_by_id(db, user_id=data["user_id"]):
        db.close()
        return jsonify({"message": "User ID does not exist."}), 400
    
    # Create consultation
    consultation = crud.create_consultation(
        db, user_id=data["user_id"], heading=data["heading"]
    )
    db.close()
    return jsonify({
        "message": "Consultation created!",
        "consultation_id": consultation.id,
        "heading": consultation.heading
    })


@main.route("/get_consultation_history/<int:consultation_id>", methods=["GET"])
def get_consultation_history(consultation_id):
    db = SessionLocal()

    # basic validation
    if consultation_id is None:
        db.close()
        return jsonify({"message": "Consultation ID is required."}), 400
    
    consultation = crud.get_consultation_by_id(db, consultation_id=consultation_id)
    if not consultation:
        db.close()
        return jsonify({"message": "Consultation ID does not exist."}), 400

    # Fetch consultation history
    consultation_timelines = crud.get_all_timeline_entries(db, consultation_id=consultation_id)
    db.close()
    return jsonify({
        "consultation": {
            "id": consultation.id,
            "heading": consultation.heading,
            "summary": consultation.summary
        },
        "timeline": [
            {
                "id": t.id,
                "user_query": t.user_query,
                "model_response": t.model_response,
                "insights": t.insights,
                "created_at": t.created_at.isoformat()
            }
            for t in consultation_timelines
        ]
    })


@main.route("/consult", methods=["POST"])
def consult():
    db = SessionLocal()
    try:
        data = request.json
        user_id = data["user_id"]
        consultation_id = data["consultation_id"]
        user_query = data["user_query"]

        result = ai.generate_consultation_response(
            db=db,
            user_id=user_id,
            consultation_id=consultation_id,
            user_query=user_query,
        )

        return jsonify({"response": result["model_response"]})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # --- PERSISTENCE BLOCK ---
        if user_query and result:

            # 1. Generate the high-density insight text for storage
            # Uses BOTH the user query and model response, plus the summarizer LLM
            insights_text = ai.extract_insights(
                user_query=user_query,
                model_response=result["model_response"]
            )
            
            # 2. Generate the final embedding vector from the CONCISE INSIGHTS text
            # This is the most accurate vector for future timeline searches.
            insight_embedding_vector = embedder.generate_embedding(insights_text)

            # 3. Store the new timeline entry
            try:
                crud.add_timeline_entry(
                    db=db,
                    consultation_id=consultation_id,
                    user_query=user_query,
                    model_response=result["model_response"],
                    insights=insights_text,
                    embedding_vector=insight_embedding_vector # Store the insight vector
                )
            except Exception as e:
                return jsonify({"error": f"error adding timeline to the database:\n {str(e)}"})

            # 4. Check for any new conditions to log for the user
            ucm_response = ucm.check_and_log_user_conditions(
                db=db,
                consultation_id=consultation_id,
                user_health_records_context=result["user_health_records_context"]
            )
            if "error" in ucm_response:
                return ucm_response
            elif "message" in ucm_response:
                print(ucm_response["message"])
            
            # 4. Check for the 10-turn threshold and summarize if needed
            mm_response = mm.manage_consultation_memory(db=db, consultation_id=consultation_id)
            if mm_response:
                if "error" in mm_response:
                    return mm_response
                elif "message" in mm_response:
                    print(mm_response["message"])

        db.close()

