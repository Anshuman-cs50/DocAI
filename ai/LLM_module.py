import os
from typing import List, Dict, Any, Optional, Literal
from flask import json
from gradio_client import Client
import requests
import re
import contextlib
import io

# Assuming RAG_SYSTEM_PROMPT_TEMPLATE and other necessary imports are available

# --- IMPORTANT: Placeholder for your LIVE Gradio URL ---
# You must update this URL every time your Colab session restarts!
# COLAB_GRADIO_URL = os.environ.get("GRADIO_API_URL", None) 
COLAB_GRADIO_URL = os.environ.get("GRADIO_API_URL") 

# HF_API_TOKEN = os.environ.get("HF_API_TOKEN", None)
HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
# Note: You should set GRADIO_API_URL in your environment for production use, 
# or hardcode the temporary URL for quick testing.

# pydantic format for Data Processing LLM
from pydantic import BaseModel, Field

# Updated model for maximum compression and searchability
class ExtractionInsights(BaseModel):
    """Schema for highly compressed, searchable insights from a conversation turn."""
    insight_found: bool = Field(description="Set to TRUE only if the conversation turn contains clinical facts, symptom changes, medication changes, or new recommendations. Set to FALSE if the response is trivial (e.g., 'Yes', 'Thank you', 'How can I help?').")
    compressed_summary: str = Field(description="A 1-3 line summary of the most important clinical facts, symptom descriptions, and final action/recommendation made in this turn. Only populate if insight_found is TRUE.")
    primary_condition_or_symptom: str = Field(description="The core medical condition, symptom (e.g., 'persistent cough'), or medication being addressed in this turn.")
    icd_codes_extracted: List[str] = Field(description="A list of 1-3 relevant ICD-10 codes mentioned or inferred from the discussion (e.g., R05 for cough, I10 for hypertension).")

class ConditionAction(BaseModel):
    """
    Schema for a single condition requiring an ADD or UPDATE action in the database.
    This model must match the fields expected by the persistence logic.
    """
    mode: Literal["add", "update", "ignore"] = Field(
        description="The action to be taken: 'add' for new conditions/symptoms; 'update' for changes to existing ones (e.g., status change); 'ignore' if the finding is trivial or already confirmed."
    )

    # Fields required for ADDING a new condition
    condition_name: str = Field(
        description="The formal medical name or symptom name (required for 'add' mode). Example: 'Lisinopril-induced cough'."
    )
    condition_type: Literal["condition", "symptom", "adr"] = Field(
        description="The clinical classification (required for 'add' mode): 'condition' (chronic/acute), 'symptom' (transient), or 'adr' (Adverse Drug Reaction)."
    )

    # Fields required for UPDATING an existing condition
    condition_id: Optional[int] = Field(
        None, description="The internal database ID of the existing condition to update (required for 'update' mode)."
    )

    # Shared optional fields (populated by LLM for richer context)
    is_active: bool = Field(
        True, description="Whether the condition is currently active. Defaults to True for new conditions."
    )
    notes: str = Field(
        "", description="Freeform clinical notes about the condition, such as severity or context."
    )


# ---- MODEL PROMPTS BASED ON CONTEXT ----
RAG_SYSTEM_PROMPT_TEMPLATE = """You are **MedGemma**, a highly specialized medical consultation assistant. Your primary function is to interpret a user's health query in light of their structured medical history.

### ROLE AND GUIDELINES
1.  **Professional Tone:** Maintain a compassionate, objective, and professional tone at all times.
2.  **Context Mandate:** You MUST prioritize and synthesize information found in the 'HISTORICAL HEALTH RECORDS' context to answer the 'USER QUERY'. The records provided have been pre-filtered for relevance (cosine similarity > 0.50) and limited to the best 4 pieces of context.
3.  **Safety First (Crucial):**
    * **NEVER** provide definitive diagnoses, specific treatment dosages, or medical advice that should only come from a licensed practitioner.
    * Frame all responses as **informational, contextual, and suggestive** (e.g., "Based on your records, the treatment for your previously documented condition of [X] typically involves...", or "This symptom could be related to...").
    * If the answer CANNOT be sufficiently grounded in the provided context or chat history, you MUST state that you lack the specific information and advise the user to consult their physician.
4.  **History Use:** Use 'CURRENT SESSION HISTORY' and 'CURRENT SESSION METADATA' to maintain continuity and context for follow-up questions.
5.  **Output Format:** Keep the response concise, clinically accurate, and easily readable.

--- CONTEXT: CURRENT SESSION METADATA (For Continuity) ---
{current_consultation_context}
    
--- CONTEXT: CURRENT SESSION HISTORY (Last 5 Turns) ---
{timeline_context}
    
--- CONTEXT: HISTORICAL HEALTH RECORDS (Top 4 Relevant Chunks) ---
{user_health_records_context}
    
--- USER QUERY ---
{user_query}

### YOUR RESPONSE:
"""

INSIGHTS_EXTRACTION_PROMPT_TEMPLATE = """You are a highly efficient medical data compression expert. Your sole task is to analyze a single user interaction turn (query and response) and extract highly compressed, structured insights.

### INSTRUCTIONS:
1.  **Conditional Extraction:** First, evaluate the content. If the conversation turn is trivial (e.g., "Yes," "No," "Okay," "Thank you," or simple greetings), set the `insight_found` field to **FALSE** and leave `compressed_summary` and `primary_condition_or_symptom` empty.
2.  **Compression Mandate:** If an insight is found, set `insight_found` to **TRUE**. The `compressed_summary` field MUST be concise, covering the core clinical finding (symptom change, medication context, or medical advice) in a maximum of **three lines**. This is the text used for future semantic search.
3.  **Output Format:** The output MUST be a single JSON object strictly matching the provided schema. Do not include any explanatory text, markdown formatting (like ```json), or chatter outside of the JSON object.

--- CONVERSATION TURN ---
USER QUERY: {user_query}
MODEL RESPONSE: {model_response}

--- JSON SCHEMA ---
{schema_json}

OUTPUT:
"""

CONDITION_DETECTION_PROMPT_TEMPLATE = """
You are a highly specialized Medical Entity Extraction System. Your task is to analyze the consultation data and determine the necessary database actions (ADD or UPDATE) for conditions and significant symptoms.

### INSTRUCTIONS:
1.  **Action Mandate:** Your primary output is a JSON list of actions (`mode`).
2.  **'add' Mode:** Use 'add' for any **new condition, new symptom, or new adverse drug reaction (ADR)** strongly suggested in the **NEW CONVERSATION ENTRIES** that is *not* clearly documented in the **HISTORICAL RECORDS**. For 'add', provide `condition_name` and `condition_type`.
3.  **'update' Mode:** Use 'update' if the NEW ENTRIES suggest a **change in status** for a condition clearly identifiable in the **HISTORICAL RECORDS** (e.g., resolution, recurrence, or explicit ID provided). For 'update', you must invent a placeholder `condition_id` (e.g., 101, 102) to signify an update is required. *NOTE: The calling function will replace this placeholder ID with the actual database ID.*
4.  **'ignore' Mode:** Use 'ignore' for trivial findings or conditions already fully addressed by the existing history.
5.  **Format:** The output MUST be a **JSON list** of objects strictly matching the provided schema. Do not include any text, markdown, or chatter outside of the JSON block.

--- CONTEXT DATA FOR ANALYSIS ---

**1. CONSULTATION SUMMARY:**
{summary_context}

**2. NEW CONVERSATION ENTRIES (Model Responses):**
{new_entries_context}

**3. HISTORICAL HEALTH RECORDS (For determining novelty):**
{user_health_records_context}

--- JSON SCHEMA (Output MUST be a list of these objects) ---
{schema_json}

OUTPUT:
"""

SUMMARIZATION_PROMPT_TEMPLATE = """
You are a highly efficient **Clinical Summarization Engine**. Your task is to update the 'EXISTING SUMMARY' by logically integrating all new clinical information and context from the 'CONVERSATION TIMELINE'.

### INSTRUCTIONS:
1.  **Cumulative Focus:** The output must be a single, cohesive narrative that replaces the existing summary.
2.  **Clinical Relevance:** Focus strictly on **chief complaints, symptom changes, medication discussions, key findings from the RAG context, and final recommendations.** Exclude conversational filler.
3.  **Conciseness:** The final summary should be limited to **3 to 5 sentences** (maximum 80 words) to maintain scannability.
4.  **Format:** Do not include any headings, bullet points, or introductory phrases. Start directly with the summary text only.

--- EXISTING SUMMARY (To be updated) ---
{existing_summary}

--- CONVERSATION TIMELINE (New Entries) ---
{conversation_timeline}

--- NEW CUMULATIVE SUMMARY ---
"""



class ConsultationLLM:
    """Handles RAG-based consultation responses using MedGemma via Gradio API."""
    
    def __init__(self, model_name: str = "medgemma-4b-it", gradio_url: str = COLAB_GRADIO_URL):
        self.model_name = model_name
        self.gradio_url = gradio_url
        print(f"Initializing remote LLM client for {self.model_name} at: {self.gradio_url}")
        try:
            import logging
            logging.getLogger("httpx").setLevel(logging.WARNING)
            # Initialize the Gradio Client quietly by swallowing stdout
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.client = Client(self.gradio_url)
        except Exception as e:
            print(f"Warning: Could not initialize Gradio Client. Ensure current URL ({self.gradio_url}) is correct. Error: {e}")
            self.client = None

    def update_gradio_url(self, new_url: str) -> bool:
        """
        Hot-reloads the Gradio client with a new URL.
        Called by the /update_gradio_url endpoint so a new Kaggle session URL
        takes effect without restarting the Flask server.
        Returns True on success, False on failure.
        """
        print(f"[INFO] Updating Gradio URL: {self.gradio_url} → {new_url}")
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                new_client = Client(new_url)
            self.client = new_client
            self.gradio_url = new_url
            print(f"[OK] Gradio client successfully re-initialized at: {new_url}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to connect to new Gradio URL ({new_url}): {e}")
            return False
            
    def generate_consultation_response(
        self,
        query: str,
        health_records_context: str,
        current_consultation_context: str,
        timeline_context: str,
    ) -> str:
        """
        Constructs the RAG prompt and calls the remote Gradio API.

        Args:
            query: The raw user query text.
            health_records_context: Pre-formatted string from ai.format_health_records_context().
                                   Injected directly into the RAG prompt.
            current_consultation_context: Pre-formatted string describing the current session.
            timeline_context: Pre-formatted string of recent conversation turns.

        Returns:
            The model's response string, or an error message string.
        """
        if not self.client:
            return "Error: Gradio client not initialized. Ensure GRADIO_API_URL is set and /update_gradio_url has been called."

        # Use a fallback if context is empty
        resolved_health_context = health_records_context or "No highly relevant historical records found (Similarity < 0.50)."

        # Build the full prompt from the template
        final_prompt = RAG_SYSTEM_PROMPT_TEMPLATE.format(
            current_consultation_context=current_consultation_context,
            timeline_context=timeline_context or "No prior history in this session.",
            user_health_records_context=resolved_health_context,
            user_query=query,
        )

        try:
            generated_text = self.client.predict(
                final_prompt,
                api_name="/predict",
            )
            return generated_text
        except Exception as e:
            return f"Error connecting to Gradio API at {self.gradio_url}: {e}"
        

class DataProcessingLLM:
    def __init__(self, model_name: str = "Qwen/Qwen2.5-7B-Instruct"):
        self.model_name = model_name
        self.api_url = "https://router.huggingface.co/v1/chat/completions"
        
        # HF_API_TOKEN is only strictly needed if not using huggingface-cli login
        # We suppress the explicit print to avoid terminal noise.
        # if 'HF_API_TOKEN' not in globals() or not HF_API_TOKEN:
        #    print("[WARNING] HF_API_TOKEN not set explicitly in globals.")

    def _clean_and_parse_json(self, raw_text: str):
        """Extracts JSON from text that might contain markdown or chatter."""
        try:
            # Use regex to find the first '{' or '[' and the last '}' or ']'
            match = re.search(r'(\{.*\}|\[.*\])', raw_text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            return json.loads(raw_text)
        except (AttributeError) as e:
            print(f"[ERROR] JSON Parsing failed: {e}")
            return None

    def _call_hf_api(self, prompt: str, schema_json: Optional[Dict[str, Any]] = None) -> str:
        headers = {
            "Authorization": f"Bearer {HF_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            # Parse OpenAI-compatible chat completion response
            raw_output = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return raw_output.strip()
            
        except Exception as e:
            print(f"API Call Failed: {e}")
            return f'{{"error": "{str(e)}"}}'

    def extract_insights(self, user_query: str, model_response: str) -> ExtractionInsights:
        prompt = INSIGHTS_EXTRACTION_PROMPT_TEMPLATE.format(
            user_query=user_query,
            model_response=model_response,
            schema_json=ExtractionInsights.model_json_schema()
        )
        
        raw_text = self._call_hf_api(prompt, schema_json=ExtractionInsights.model_json_schema())
        data = self._clean_and_parse_json(raw_text)
        
        # Guard against API failures returning {"error": "..."} dicts
        if not data or "error" in data:
            if "error" in (data or {}):
                print(f"[WARNING] API Error during extraction: {data['error']}")
            return ExtractionInsights(
                insight_found=False,
                compressed_summary="",
                primary_condition_or_symptom="",
                icd_codes_extracted=[]
            )
            
        return ExtractionInsights(**data)

    def detect_condition(self, summary_context: str, new_entries_context: List[str], user_health_records_context: List[Dict[str, Any]]) -> List[ConditionAction]:
        # Handle list vs string formatting
        new_entries_str = "\n".join(new_entries_context) if isinstance(new_entries_context, list) else str(new_entries_context)
        user_health_str = json.dumps(user_health_records_context, indent=2)

        prompt = CONDITION_DETECTION_PROMPT_TEMPLATE.format(
            summary_context=summary_context,
            new_entries_context=new_entries_str,
            user_health_records_context=user_health_str,
            schema_json=ConditionAction.model_json_schema()
        )

        raw_text = self._call_hf_api(prompt, schema_json=ConditionAction.model_json_schema())
        data = self._clean_and_parse_json(raw_text)

        # Guard against API failures returning {"error": "..."} dicts
        if not data or (isinstance(data, dict) and "error" in data):
            if isinstance(data, dict) and "error" in data:
                print(f"[WARNING] API Error during detection: {data['error']}")
            return []
        
        # Ensure result is a list even if LLM returned a single object
        items = data if isinstance(data, list) else [data]
        return [ConditionAction(**item) for item in items]

    def summarise(self, existing_summary: str, formatted_timeline: str) -> str:
        """
        Generates an updated cumulative clinical summary.

        Args:
            existing_summary: The current summary stored in the database.
            formatted_timeline: A pre-formatted string of recent conversation turns,
                               produced by MemoryManager.format_timeline_for_summarization().

        Returns:
            Updated summary string, or the original if no new content.
        """
        if not formatted_timeline:
            return existing_summary

        prompt = SUMMARIZATION_PROMPT_TEMPLATE.format(
            existing_summary=existing_summary or "None.",
            conversation_timeline=formatted_timeline,
        )

        raw_text = self._call_hf_api(prompt)
        # Strip common LLM artifacts (headings, trailing separators)
        clean_summary = raw_text.strip().split("---")[-1].strip()
        return clean_summary if clean_summary else existing_summary

if __name__ == "__main__":
    # Note: Since this block is meant for testing, we will mock the
    # self._call_hf_api method to return fixed JSON strings to simulate 
    # successful LLM responses without needing a live API key.

    class MockDataProcessingLLM(DataProcessingLLM):
        """Mocks the LLM to return predetermined, structured responses for testing."""
        def __init__(self, *args, **kwargs):
            # Bypass the real init setup (like checking HF_API_TOKEN)
            super().__init__(*args, **kwargs)
            print("\n--- MOCK LLM INITIALIZED FOR OFFLINE TESTING ---")

        # --- MOCK LLM INITIALIZED FOR OFFLINE TESTING ---
        def _call_hf_api(self, prompt: str, schema_json: Optional[Dict[str, Any]] = None) -> str:
            """Mocks API call to return structured test data."""
            
            # --- Test Case 1: INSIGHTS EXTRACTION (Check for 'CONVERSATION TURN' heading) ---
            if "--- CONVERSATION TURN ---" in prompt: 
                # Insight found: User reports cough is a side effect of Lisinopril.
                return json.dumps({
                    "insight_found": True,
                    "compressed_summary": "Patient noted onset of dry, persistent cough beginning 3 days after starting Lisinopril 5mg. Patient stopped the drug immediately.",
                    "primary_condition_or_symptom": "Lisinopril-induced cough (Adverse Drug Reaction)",
                    "icd_codes_extracted": ["R05", "T46.4X5A"]
                })

            # --- Test Case 2: CONDITION DETECTION (Check for 'CONTEXT DATA FOR ANALYSIS' heading) ---
            elif "--- CONTEXT DATA FOR ANALYSIS ---" in prompt: 
                # Two conditions detected: one to ADD, one to IGNORE (because it's old news)
                return json.dumps([
                    {
                        "mode": "add",
                        "condition_name": "Dry, Persistent Cough (Lisinopril-induced)",
                        "condition_type": "adr",
                        "condition_id": None,
                        "icd_code_estimate": "R05",
                        "is_active": True,
                        "notes": "ADR strongly suspected from new entries; patient ceased drug.",
                        "certainty_level": 0.95
                    },
                    {
                        "mode": "ignore",
                        "condition_name": "Hypertension",
                        "condition_type": "condition",
                        "condition_id": 101,
                        "icd_code_estimate": "I10",
                        "is_active": True,
                        "notes": "Existing chronic condition; no change in status detected.",
                        "certainty_level": 0.30
                    }
                ])

            # --- Test Case 3: CUMULATIVE SUMMARIZATION (Check for 'EXISTING SUMMARY' heading) ---
            elif "--- EXISTING SUMMARY (To be updated) ---" in prompt:
                return (
                    "Patient presented with a new onset of dry, persistent cough three days after initiating Lisinopril 5mg for Grade 1 Hypertension. The cough was non-productive, severe at night, and resolved quickly upon cessation of the medication. The physician recommended discontinuing Lisinopril and transitioning to Losartan 25mg daily instead. The patient was advised to follow up in two weeks to check the blood pressure response to the new regimen."
                )

            return '{"error": "No mock response defined for this prompt."}' # This is the fall-through error that was causing the failure.

    print("--- Starting DocAI DataProcessingLLM Test ---")
    
    # Initialize the LLM class
    processor = DataProcessingLLM()
    
    # Test Data
    test_query = "I have been feeling a sharp pain in my lower back for three days."
    test_response = "It sounds like you might have acute lower back pain (ICD-10: M54.5). I recommend rest and monitoring."

    print(f"\n[TEST 1] Extracting Insights...")
    insights = processor.extract_insights(test_query, test_response)

    print(f"Insight Found: {insights.insight_found}")
    print(f"Summary: {insights.compressed_summary}")
    print(f"Condition: {insights.primary_condition_or_symptom}")
    print(f"ICD Codes: {insights.icd_codes_extracted}")

    print("\n--- Test Complete ---")