import os
from typing import List, Dict, Any, Optional, Literal
from flask import json
from gradio_client import Client
import requests
# Assuming RAG_SYSTEM_PROMPT_TEMPLATE and other necessary imports are available

# --- IMPORTANT: Placeholder for your LIVE Gradio URL ---
# You must update this URL every time your Colab session restarts!
COLAB_GRADIO_URL = os.environ.get("GRADIO_API_URL", None) 

HF_API_TOKEN = os.environ.get("HF_API_TOKEN", None)
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
    
    # Fields used for both ADD or UPDATE
    icd_code_estimate: Optional[str] = Field(
        None, description="The estimated ICD-10 code (e.g., R05 for cough)."
    )
    is_active: bool = Field(
        True, description="The current status of the condition: True if ongoing/new, False if resolved/inactive."
    )
    notes: str = Field(
        description="Brief (max 1 sentence) clinical notes on the source of the finding."
    )
    certainty_level: float = Field(
        description="A confidence score (0.0 to 1.0) on the certainty of this action based on the analyzed text."
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
            # Initialize the Gradio Client
            self.client = Client(self.gradio_url)
        except Exception as e:
            print(f"Warning: Could not initialize Gradio Client. Ensure current URL ({self.gradio_url}) is correct. Error: {e}")
            self.client = None
            
    def generate_consultation_response(
        self,
        query: str,
        context_list: List[Dict[str, Any]],
        current_consultation_context: str,
        timeline_context: str
    ) -> str:
        """
        Constructs the RAG prompt and calls the remote Gradio API.
        """
        if not self.client:
            return "Error: Gradio client not initialized. Check the COLAB_GRADIO_URL."

        # Format the historical records context
        if not context_list:
            user_health_records_context = 'No highly relevant historical records found (Similarity < 0.50).'
        else:
            user_health_records_context = "\n".join([
                f"SOURCE_TYPE: {c['type']} | TITLE: {c['title']}\n"
                f"RELEVANCE: {c['relevance_similarity']:.4f}\n"
                f"SNIPPET: {c['snippet']}"
                for c in context_list
            ])
            
        # 1. Substitute all fields into the template to create the full text_prompt
        final_prompt = RAG_SYSTEM_PROMPT_TEMPLATE.format(
            current_consultation_context=current_consultation_context,
            timeline_context=timeline_context or 'No prior history in this session.',
            user_health_records_context=user_health_records_context or 'No related record.',
            user_query=query
        )
        
        # 2. Call the remote Gradio API using the client.predict method
        try:
            # The client.predict call must match the inputs of your Colab Gradio interface.
            # Assuming your Colab interface accepts a single string prompt (text_prompt) 
            # and uses the default '/predict' API endpoint.
            generated_text = self.client.predict(
                final_prompt,
                api_name="/predict"
            )
            
            # Note: You may need to adjust how the output is extracted based on 
            # how your Gradio function returns the text (e.g., if it's nested).
            return generated_text 

        except Exception as e:
            return f"Error connecting to Gradio API at {self.gradio_url}: {e}"


class DataProcessingLLM:
    """Handles structured data extraction and summarization."""
    def __init__(self, model_name: str = "meta-llama/Meta-Llama-3-8B-Instruct"):
        self.model_name = model_name
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_name}"
        # Added check for Gradio URL as well for completeness
        if HF_API_TOKEN is None:
            print("🛑 WARNING: HF_API_TOKEN is not set in environment variables. Data Processing API calls will fail.")
        if COLAB_GRADIO_URL is None:
             print("⚠️ WARNING: GRADIO_API_URL is not set.")

    def _call_hf_api(self, prompt: str, schema_json: Optional[Dict[str, Any]] = None) -> str:
        """
        Internal method to call the Hugging Face Inference API.
        
        It conditionally configures the payload for structured JSON output 
        (using the 'response_format' parameter) if a schema is provided.
        
        Args:
            prompt: The full prompt text to send to the LLM.
            schema_json: The Pydantic model's .schema() output (as a dictionary) 
                         if structured JSON is required, otherwise None.
                         
        Returns:
            The raw generated text or JSON string from the model, or an error message.
        """
        if not HF_API_TOKEN:
            return '{"error": "HF_API_TOKEN not configured."}'

        # 1. Define base payload parameters
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 1024,
                "temperature": 0.1,  # Low temperature is best for factual extraction/summarization
                "return_full_text": False
            }
        }
        
        # 2. Add JSON structure request if a schema is provided
        if schema_json:
            # Llama 3 models support the 'response_format' parameter for guaranteed JSON output
            payload["parameters"]["response_format"] = {
                "type": "json_object",
                "schema": schema_json
            }
        
        # 3. Define headers using the API token
        headers = {
            "Authorization": f"Bearer {HF_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # 4. Execute the API call
        try:
            # self.api_url should be defined in __init__ (e.g., https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct)
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            
            # HF API returns a list containing one dictionary result
            result = response.json()
            if isinstance(result, list) and result:
                # The response text, which should be the generated output/JSON string
                return result[0].get('generated_text', '').strip()
            
            # Handle cases where the response structure is unexpected
            return f'{{"error": "Unexpected API response structure: {str(result)}"}}'
        
        except requests.exceptions.HTTPError as e:
            # Log specific HTTP errors (e.g., model loading, invalid input)
            error_details = response.json().get("error", str(e))
            print(f"API HTTP Error ({response.status_code}): {error_details}")
            return f'{{"error": "API HTTP Request Failed: {error_details}"}}'
            
        except requests.exceptions.RequestException as e:
            # Log general connection errors
            print(f"API Connection Error: {e}")
            return f'{{"error": "API Connection Failed: {e}"}}'

    def detect_condition(self, summary_context: str, new_entries_context: List[str], user_health_records_context: List[Dict[str, Any]]) -> List[ConditionAction]:
        # ... (Context formatting remains the same) ...

        # 2. Format the full prompt using the template and the Pydantic schema
        prompt = CONDITION_DETECTION_PROMPT_TEMPLATE.format(
            summary_context=summary_context,
            new_entries_context=new_entries_context,
            user_health_records_context=user_health_records_context,
            schema_json=ConditionAction.model_json_schema()
        )

        # 3. Call the API (CRITICAL FIX HERE: Use .schema() instead of .schema_json())
        raw_json = self._call_hf_api(prompt, schema_json=ConditionAction.model_json_schema()) # FIXED
        
        # ... (Parsing and validation remain the same) ...
        try:
            data = json.loads(raw_json)
            if not isinstance(data, list):
                data = [data]
            return [ConditionAction(**item) for item in data]
        except Exception as e:
            print(f"Failed to parse JSON for detect_condition: {e}. Raw output: {raw_json}")
            return []


    def summarise(
        self, 
        existing_summary: str, 
        # CRITICAL FIX HERE: Reverting type to the robust list of dicts for conversation history
        new_timeline_entries: List[Dict[str, str]] 
    ) -> str:
        """
        Generates a new, cumulative summary by combining the existing summary 
        with recent conversation turns via the Hugging Face API.
        """
        
        # 1. Format the new timeline entries into a readable string
        timeline_context = ""
        for entry in new_timeline_entries:
            # Assuming entries contain 'user_query' and 'model_response' keys (adjust keys if needed)
            timeline_context += f"User: {entry.get('user_query', 'N/A')}\n"
            timeline_context += f"Assistant: {entry.get('model_response', 'N/A')}\n"
        
        if not timeline_context:
            return existing_summary

        # 2. Format the final prompt
        prompt = SUMMARIZATION_PROMPT_TEMPLATE.format(
            existing_summary=existing_summary or "None.",
            conversation_timeline=timeline_context
        )

        # 3. Call the API (Passing schema_json=None for text generation)
        try:
            raw_text = self._call_hf_api(prompt, schema_json=None) 
            
            # Check for error message returned by _call_hf_api
            if '{"error":' in raw_text:
                 raise Exception(raw_text)

            return raw_text.strip().replace('"', '').replace("'", "")
            
        except Exception as e:
            print(f"Error during summarization LLM call: {e}")
            return existing_summary

    def extract_insights(self, user_query: str, model_response: str) -> ExtractionInsights:
        # ... (This method is fine, as it correctly uses .schema() for the API call) ...
        
        # 1. Format the full prompt using the template and the Pydantic schema
        prompt = INSIGHTS_EXTRACTION_PROMPT_TEMPLATE.format(
            user_query=user_query,
            model_response=model_response,
            schema_json=ExtractionInsights.model_json_schema()
        )

        # 2. Call the API (Correctly using .schema() for the API payload)
        raw_json = self._call_hf_api(prompt, schema_json=ExtractionInsights.model_json_schema()) # Correct

        # ... (Parsing and validation remain the same) ...
        try:
            data = json.loads(raw_json)
            return ExtractionInsights(**data)
        except Exception as e:
            print(f"Failed to parse JSON for extract_insights: {e}. Raw output: {raw_json}")
            # Return a default/error structure
            return ExtractionInsights(
                insight_found=False,
                compressed_summary="Extraction failed due to parsing error.",
                primary_condition_or_symptom="Unknown Error",
                icd_codes_extracted=[]
            )

# if __name__ == "__main__":
#     # --- Configuration ---
#     # !!! IMPORTANT: REPLACE THIS with your LIVE, temporary Gradio URL from Colab !!!
#     LIVE_GRADIO_URL = "https://824aee39f4227272a5.gradio.live/" 

#     if LIVE_GRADIO_URL == "YOUR_LIVE_GRADIO_URL_HERE":
#         print("🛑 WARNING: Please replace 'YOUR_LIVE_GRADIO_URL_HERE' with your actual Gradio link from Colab.")
#         # We can't proceed with the live call without the correct URL.
    
#     # --- 1. Instantiate the remote LLM client ---
#     consultation_llm = ConsultationLLM(gradio_url=LIVE_GRADIO_URL) 

#     # --- 2. Define Context Placeholders (Synthetic Data) ---
    
#     current_consultation_context = (
#         "Patient Name: Anshuman. Current Chief Complaint: New onset of persistent cough and mild chest tightness."
#     )

#     timeline_context = (
#         "User: It started about 3 days ago, and yes, I'm taking the Lisinopril for my blood pressure.\n"
#         "MedGemma: Thank you. Do you recall any previous times you had a prolonged cough?"
#     )

#     context_list: List[Dict[str, Any]] = [
#         {
#             "type": "Medication Record",
#             "title": "Lisinopril Prescription",
#             "snippet": "Patient started on Lisinopril 10mg daily on 2024-03-15 for essential hypertension. Side effect profile includes dry, persistent cough in <5% of users. Advised to monitor for this.",
#             "relevance_distance": 0.2291,
#             "relevance_similarity": 0.7709
#         },
#         {
#             "type": "Consultation Summary",
#             "title": "Annual Physical 2024",
#             "snippet": "No cardiac murmurs noted. Lungs were clear to auscultation. Patient advised to maintain low-sodium diet and continue blood pressure management.",
#             "relevance_distance": 0.3148,
#             "relevance_similarity": 0.6852
#         },
#         {
#             "type": "Diagnostic Report",
#             "title": "Chest X-Ray 2023",
#             "snippet": "Chest X-ray clear. No signs of consolidation, fluid, or cardiomegaly.",
#             "relevance_distance": 0.4489,
#             "relevance_similarity": 0.5511
#         },
#     ]

#     user_query = "This cough is really getting annoying and I also feel a little tight in the chest. Should I stop taking my Lisinopril immediately?"
    
#     # --- 3. Call the function ---
#     print("\n" + "="*50)
#     print("🤖 Calling Remote MedGemma via Gradio API...")
#     print(f"Target URL: {LIVE_GRADIO_URL}")
#     print("="*50)

#     response = consultation_llm.generate_consultation_response(
#         query=user_query,
#         context_list=context_list,
#         current_consultation_context=current_consultation_context,
#         timeline_context=timeline_context
#     )

#     print("\n" + "="*50)
#     print("✅ MEDGEMMA GENERATED RESPONSE (from Colab API):")
#     print("="*50)
#     print(response)
#     print("="*50)


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

    llm_processor = MockDataProcessingLLM()

    print("\n=========================================================================================")
    print("🚀 STARTING DataProcessingLLM TEST BLOCK")
    print("=========================================================================================")

    # --- TEST 1: extract_insights ---
    print("\n### 1. TESTING INSIGHTS EXTRACTION")
    user_query_1 = "I think my new blood pressure pill, the Lisinopril 5mg, is giving me a constant dry cough. Should I stop it?"
    model_response_1 = "Based on your medical history, a dry cough is a common side effect of Lisinopril. Please discontinue the medication immediately and contact your primary care physician to discuss switching to an alternative such as Losartan."
    
    insights = llm_processor.extract_insights(user_query_1, model_response_1)
    
    print("\n--- Insight Result ---")
    print(f"Insight Found: {insights.insight_found}")
    print(f"Condition:     {insights.primary_condition_or_symptom}")
    print(f"Summary:       {insights.compressed_summary}")
    print(f"ICD Codes:     {insights.icd_codes_extracted}")
    print("-" * 20)


    # --- TEST 2: detect_condition ---
    print("\n### 2. TESTING CONDITION DETECTION (ADD/IGNORE)")
    summary_context_2 = "Initial consultation summary. Patient is a 55-year-old male with a history of Grade 1 Hypertension (diagnosed 2 years ago) currently managed with diet and exercise."
    new_entries_context_2 = [model_response_1] # Use the response from Test 1 as new entry
    user_health_records_context_2 = [
        {"type": "Condition", "title": "Hypertension (Grade 1)", "snippet": "Diagnosed in 2023. Currently controlled with lifestyle changes. ID: 101"},
        {"type": "Medication", "title": "Lisinopril 5mg", "snippet": "Started 3 days ago for BP management. ID: 205"}
    ]
    
    conditions = llm_processor.detect_condition(
        summary_context_2,
        new_entries_context_2,
        user_health_records_context_2
    )
    
    print("\n--- Condition Detection Result ---")
    print(f"Detected {len(conditions)} potential action(s):")
    for c in conditions:
        print(f"  - Action:    {c.mode.upper()} (Certainty: {c.certainty_level})")
        print(f"    Name:      {c.condition_name}")
        print(f"    Type:      {c.condition_type}")
        if c.condition_id is not None:
            print(f"    DB ID:     {c.condition_id}")
    print("-" * 20)
    
    
    # --- TEST 3: summarise ---
    print("\n### 3. TESTING CUMULATIVE SUMMARIZATION")
    existing_summary_3 = "Patient initiated consult due to new diagnosis of Grade 1 Hypertension. Started Lisinopril 5mg 3 days ago."
    new_timeline_entries_3 = [
        {"query": user_query_1, "response": model_response_1}, # The turn from Test 1
        {"query": "What about Losartan? Is that safer?", "response": "Losartan is an ARB, which works differently and typically does not cause the same cough side effect. It is a suitable alternative for your blood pressure."}
    ]
    
    new_summary = llm_processor.summarise(existing_summary_3, new_timeline_entries_3)
    
    print("\n--- Summarization Result ---")
    print("--------------------------------------------------------------------------------------------------------------------------------")
    print(new_summary)
    print("--------------------------------------------------------------------------------------------------------------------------------")
    print("\n=========================================================================================")
    print("✅ DataProcessingLLM MOCK TESTS COMPLETE")
    print("=========================================================================================")