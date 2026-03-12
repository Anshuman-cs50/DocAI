import re
import json
from gradio_client import Client

def robust_json_parser(text):
    """Safety net to find JSON if the model includes chatter or code blocks."""
    try:
        # 1. Try direct parsing
        return json.loads(text)
    except json.JSONDecodeError:
        # 2. Try to find anything between { } or [ ]
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
    return None

def run_docai_integration_test(gradio_url: str):
    client = Client(gradio_url)
    
    # Test Case: Extraction
    prompt = "Extract insights for: 'Patient has a sharp cough and mild fever' into JSON schema."
    raw_output = client.predict(prompt, api_name="/predict")
    
    print(f"--- Raw Output ---\n{raw_output}\n-----------------")
    
    data = robust_json_parser(raw_output)
    if data:
        print("✅ Success! Extracted JSON even with chatter.")
        print(f"Primary Symptom: {data.get('primary_condition_or_symptom', 'Not found')}")
    else:
        print("❌ Still failing to get clean JSON. Check Colab logs.")

if __name__ == "__main__":
    URL = input("Enter your Gradio URL: ").strip()
    run_docai_integration_test(URL)