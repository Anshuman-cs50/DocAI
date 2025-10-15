from flask import request, jsonify
from datetime import datetime
import db_ops
from chat_utils import generate_ai_consult_response



def consult_endpoint(user_id, user_query):
    """
    Handles a full, new consultation request. Always starts a new, completed record.
    """
    try:
        
        if not db_ops.validate_user(user_id):
            return jsonify({"message": "Unauthorized user"}), 401

        # 1. Start a new, fresh consultation record
        consultation_id = db_ops.start_consultation_session(user_id)
        
        # 2. Get past data context using db_ops
        past_summaries = db_ops.get_consultation_summary(user_id, consultation_id)
        context = " ".join(past_summaries) if past_summaries else ""

        # 3. Retrieve detailed health matrix 
        user_health_matrix = db_ops.get_user_health_matrix(user_id, user_query)

        # 4. Prompt the AI
        ai_consult_data = generate_ai_consult_response(query=user_query, context=context, health_matrix=user_health_matrix)
        ai_response_text = ai_consult_data.get("solution_for_user", "No response from AI.")
        
        # 5. Store the final result (Summary and set status to completed)
        summary = f"CONSULTATION QUERY: {user_query}\n---\nAI RESPONSE: {ai_consult_data.get('conversation_summary')}"
        
        # Manually update status and summary using raw SQLite access
        db = db_ops.get_db()
        cursor = db.cursor()
        cursor.execute("""
            UPDATE consultation_records
            SET summary = ?, status = 'completed', time_completed = ?
            WHERE consultation_id = ?
        """, (summary, datetime.utcnow().isoformat(), consultation_id))
        db.commit()

        return jsonify({
            "consultation_id": consultation_id,
            "ai_consult_response": ai_response_text,
            "message": "Consultation finalized and stored."
        }), 200

    except Exception as e:
        return jsonify({"error": "Internal Server Error during consult", "details": str(e)}), 500
    


print(consult_endpoint(1, "I have been experiencing frequent headaches and dizziness. What could be the cause?"))