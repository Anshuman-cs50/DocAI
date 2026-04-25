# app/routes.py
import os
from flask import Blueprint, jsonify, request, render_template
from db.database import SessionLocal
from db import crud, models
from ai import ai, MemoryManager as mm, UserConditionManager as ucm
from ai.post_processing import run_end_of_session_pipeline
import threading
from werkzeug.security import generate_password_hash, check_password_hash

main = Blueprint("main", __name__)


@main.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@main.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


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


@main.route("/signup", methods=["POST"])
def signup():
    db = SessionLocal()
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    
    if not name or not email or not password:
        db.close()
        return jsonify({"message": "Name, email, and password are required."}), 400
    
    if crud.get_user_by_email(db, email=email):
        db.close()
        return jsonify({"message": "Email already registered."}), 400
    
    # Hash the password
    password_hash = generate_password_hash(password)
    
    # Extract metadata fields
    age = data.get("age")
    gender = data.get("gender")
    blood_type = data.get("blood_type")
    height_cm = data.get("height_cm")
    weight_kg = data.get("weight_kg")
    
    # Pre-existing conditions
    pre_existing_conditions = data.get("pre_existing_conditions", [])
    
    # Create user
    user = crud.create_user(
        db, 
        name=name, 
        email=email, 
        password_hash=password_hash,
        age=age,
        gender=gender,
        blood_type=blood_type,
        height_cm=height_cm,
        weight_kg=weight_kg,
        pre_existing_conditions=pre_existing_conditions
    )
    db.close()
    
    return jsonify({
        "message": "User created successfully!",
        "user_id": user.id,
        "name": user.name,
        "email": user.email
    })

@main.route("/login", methods=["POST"])
def login():
    db = SessionLocal()
    data = request.get_json()
    
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        db.close()
        return jsonify({"message": "Email and password are required."}), 400
        
    user = crud.get_user_by_email(db, email=email)
    
    # Verify user exists and password matches
    if not user or not user.password_hash or not check_password_hash(user.password_hash, password):
        db.close()
        return jsonify({"message": "Invalid email or password."}), 401
        
    user_data = {
        "id": user.id,
        "name": user.name,
        "email": user.email
    }
    db.close()
    return jsonify({
        "message": "Login successful",
        "user": user_data
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
            model_response_text = result.get("model_response", "")
            
            # Do NOT persist if the LLM returned an error - error responses
            # poison the context window and degrade future model quality.
            # Note: errors can be wrapped in [ANSWER] tags by the second agent pass,
            # so we check for [ERROR] *anywhere* in the response.
            is_error_response = (
                not model_response_text
                or "[ERROR]" in model_response_text
                or "failed to respond" in model_response_text.lower()
            )

            if is_error_response:
                print(f"[WARN] LLM returned an error response — skipping DB write to protect context window.")
            else:
                # Simply store the raw chat for history.
                # Insight extraction & embedding generation are deferred to the end of the session.
                try:
                    crud.add_timeline_entry(
                        db=db,
                        consultation_id=consultation_id,
                        user_query=user_query,
                        model_response=model_response_text,
                        insights="Pending End-of-Session Extraction",
                        embedding_vector=None
                    )
                    print(f"[OK] Timeline entry stored.")
                except Exception as e:
                    return jsonify({"error": f"error adding timeline to the database:\n {str(e)}"}), 500
        
        db.close()

@main.route("/end_consultation", methods=["POST"])
def end_consultation():
    db = SessionLocal()
    data = request.get_json()
    consultation_id = data.get("consultation_id")
    
    if not consultation_id:
        db.close()
        return jsonify({"error": "consultation_id is required"}), 400
        
    consultation = crud.end_consultation(db, consultation_id=consultation_id)
    db.close()
    
    if not consultation:
        return jsonify({"error": "Consultation not found"}), 404
        
    # Trigger the end-of-session background pipeline
    threading.Thread(target=run_end_of_session_pipeline, args=(consultation_id,)).start()
        
    return jsonify({"message": "Consultation ended successfully"})

@main.route("/get_user_profile_by_email", methods=["POST"])
def get_user_profile_by_email():
    db = SessionLocal()
    data = request.get_json()
    email = data.get("email")
    if not email:
        db.close()
        return jsonify({"error": "Email is required"}), 400
    
    user = crud.get_user_by_email(db, email=email)
    if not user:
        db.close()
        return jsonify({"error": "User not found"}), 404
        
    return _build_user_profile_response(db, user.id)

@main.route("/update_profile", methods=["POST"])
def update_profile():
    db = SessionLocal()
    data = request.get_json()
    
    user_id = data.get("user_id")
    if not user_id:
        db.close()
        return jsonify({"error": "User ID is required"}), 400
        
    age = data.get("age")
    gender = data.get("gender")
    blood_type = data.get("blood_type")
    height_cm = data.get("height_cm")
    weight_kg = data.get("weight_kg")
    
    # Convert empty strings to None and parse numbers
    age = int(age) if age else None
    height_cm = float(height_cm) if height_cm else None
    weight_kg = float(weight_kg) if weight_kg else None
    gender = gender if gender else None
    blood_type = blood_type if blood_type else None
    
    user = crud.update_user_profile(
        db, 
        user_id=user_id,
        age=age,
        gender=gender,
        blood_type=blood_type,
        height_cm=height_cm,
        weight_kg=weight_kg
    )
    
    db.close()
    
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    return jsonify({"message": "Profile updated successfully"})

@main.route("/get_user_profile/<int:user_id>", methods=["GET"])
def get_user_profile(user_id):
    db = SessionLocal()
    user = crud.get_user_by_id(db, user_id=user_id)
    if not user:
        db.close()
        return jsonify({"error": "User not found"}), 404
        
    return _build_user_profile_response(db, user_id)

def _build_user_profile_response(db, user_id):
    user = crud.get_user_by_id(db, user_id=user_id)
    
    # Get consultations
    recent_consults = crud.get_recent_consultations(db, user_id=user_id, limit=20)
    
    valid_consults = []
    for c in recent_consults:
        # Filter out inactive consultations that have 0 timeline entries
        if not c.is_active:
            count = db.query(models.ConsultationTimeline).filter_by(consultation_id=c.id).count()
            if count == 0:
                continue
        valid_consults.append(c)
    
    # Get conditions
    # We query directly or use the relationship
    conditions = db.query(models.UserCondition).filter(models.UserCondition.user_id == user_id).all()
    
    # Get latest vitals
    vitals = crud.get_latest_vitals(db, user_id=user_id)
    
    response_data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "age": user.age,
        "gender": user.gender,
        "blood_type": user.blood_type,
        "height_cm": float(user.height_cm) if user.height_cm else None,
        "weight_kg": float(user.weight_kg) if user.weight_kg else None,
        "consultations": [
            {
                "id": c.id,
                "date": c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "",
                "title": c.heading,
                "summary": c.summary,
                "is_active": c.is_active
            }
            for c in valid_consults
        ],
        "conditions": [
            {
                "id": cond.id,
                "name": cond.condition_name,
                "active": cond.is_active,
                "type": cond.condition_type
            } for cond in conditions
        ],
        "vitals": {
            # Since get_latest_vitals returns a list of VitalsTimeSeries objects
            v.metric_name: v.metric_value for v in vitals
        } if vitals else {}
    }
    
    db.close()
    return jsonify(response_data)