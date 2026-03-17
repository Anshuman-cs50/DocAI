# app/routes.py
import os
from flask import Blueprint, jsonify, request, render_template
from db.database import SessionLocal
from db import crud
from ai import ai, MemoryManager as mm, UserConditionManager as ucm

main = Blueprint("main", __name__)


@main.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@main.route("/update_gradio_url", methods=["POST"])
def update_gradio_url():
    """
    Accepts a new Gradio URL from the Kaggle/Colab notebook and hot-reloads
    the ConsultationLLM client — no Flask server restart needed.

    Body: { "url": "https://...", "secret": "your-secret" }
    The secret must match URL_UPDATE_SECRET in .env.
    """
    expected_secret = os.getenv("URL_UPDATE_SECRET", "")
    if not expected_secret:
        return jsonify({"error": "URL_UPDATE_SECRET is not configured on the server."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    provided_secret = data.get("secret", "")
    if provided_secret != expected_secret:
        return jsonify({"error": "Unauthorized: invalid secret."}), 401

    new_url = data.get("url", "").strip()
    if not new_url:
        return jsonify({"error": "'url' field is required."}), 400

    # Hot-reload the Gradio client on the module-level singleton
    success = ai.consultation_llm.update_gradio_url(new_url)

    if success:
        # Also persist the URL to .env so it survives server restarts
        _update_env_file("GRADIO_API_URL", new_url)
        return jsonify({"status": "ok", "url": new_url})
    else:
        return jsonify({"error": f"Failed to connect to new Gradio URL: {new_url}"}), 502


def _update_env_file(key: str, value: str):
    """Updates or appends a key=value pair in the .env file."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    try:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
            updated = False
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    updated = True
                    break
            if not updated:
                lines.append(f"{key}={value}\n")
            with open(env_path, "w") as f:
                f.writelines(lines)
    except Exception as e:
        print(f"[WARNING] Could not update .env file: {e}")


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
    
    # initialise result and query variable
    result = None
    user_query = None
    
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
        
        print(f"[OK] Consultation response generated successfully.")
        return jsonify({"response": result["model_response"]})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        # --- PERSISTENCE BLOCK ---
        if user_query and result:
            # Simply store the raw chat for history. 
            # Insight extraction & embedding generation are deferred to the end of the session.
            try:
                crud.add_timeline_entry(
                    db=db,
                    consultation_id=consultation_id,
                    user_query=user_query,
                    model_response=result["model_response"],
                    insights="Pending End-of-Session Extraction",
                    embedding_vector=None
                )
                print(f"[OK] Timeline entry stored.")
            except Exception as e:
                return jsonify({"error": f"error adding timeline to the database:\n {str(e)}"}), 500
        
        db.close()