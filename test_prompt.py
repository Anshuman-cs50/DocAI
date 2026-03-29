import os
import json
from typing import List, Dict
from colorama import Fore, Style, init

# Initialize colorama for colored terminal output
init(autoreset=True)

# Import the module to be tested
from ai.LLM_module import ConsultationLLM, AGENTIC_SYSTEM_PROMPT

# Optional: Disable proxy warnings if not using Kaggle locally
import warnings
warnings.filterwarnings("ignore")

class TestResult:
    def __init__(self, test_id: str, desc: str, expected_action: str, actual_response: str):
        self.test_id = test_id
        self.desc = desc
        self.expected_action = expected_action
        self.actual_response = actual_response
        
        # Simple extraction of the chosen action 
        if "[ASK]" in actual_response:
            self.actual_action = "[ASK]"
        elif "[SEARCH]" in actual_response:
            self.actual_action = "[SEARCH]"
        elif "[ANSWER]" in actual_response:
            self.actual_action = "[ANSWER]"
        else:
            self.actual_action = "INVALID_FORMAT"
            
        self.passed = self.expected_action == self.actual_action

def run_tests():
    print(f"{Fore.CYAN}==================================================")
    print(f"{Fore.CYAN}    MedGemma / AGENTIC_SYSTEM_PROMPT Eval Suite   ")
    print(f"{Fore.CYAN}==================================================\n")
    
    # Check if we have a live URL to test against
    gradio_url = "https://d96bbd79b6dd0b0961.gradio.live"
    if not gradio_url:
        print(f"{Fore.YELLOW}[WARNING] GRADIO_API_URL environment variable is not set.")
        print("Please ensure your Colab/Kaggle endpoint is running and export the URL:")
        print("  $env:GRADIO_API_URL='https://...gradio.live'")
        print("Testing cannot proceed without the model backend.\n")
        return

    print(f"Connecting to model at: {gradio_url}...")
    llm = ConsultationLLM(gradio_url=gradio_url)
    
    if not llm.client:
        print(f"{Fore.RED}[CRITICAL] Failed to connect to Gradio client. Tests aborted.")
        return
        
    print(f"{Fore.GREEN}[OK] Connected.\n")

    # Define our test cases from the tuning framework
    
    test_cases = [
    # --- CONTEXT ACCUMULATION ---
    {
        "id": "T-19",
        "desc": "Escalation Mid-Conversation",
        "messages": [
            {
                "role": "user",
                "content": AGENTIC_SYSTEM_PROMPT + "\n\nUser Query:\nI've had a mild headache since this morning."
            },
            {
                "role": "assistant",
                "content": "[ASK] On a scale of 1-10, how would you rate the pain, and where is it located?"
            },
            {
                "role": "user",
                "content": "It started as a 3 at the back of my neck. But in the last 10 minutes it's jumped to a 9 and now it feels like it exploded."
            }
        ],
        "expected_action": "[ANSWER]",
        # Logic: The opening message was benign — mild headache, no red flags.
        # The model correctly asked a clarifying question. But the patient's SECOND
        # message describes a sudden escalation to maximal severity mid-conversation.
        # Tests whether Emergency Pattern 1 fires on follow-up turns, not just
        # the opening message. The model must not stay on the [ASK] track.
    },

    # --- CONTRADICTORY PATIENT STATEMENT ---
    {
        "id": "T-20",
        "desc": "Patient Contradicts Own Red Flag",
        "messages": [
            {
                "role": "user",
                "content": AGENTIC_SYSTEM_PROMPT + "\n\nUser Query:\nI had the worst chest pain of my life about 20 minutes ago but I took an antacid and it went away completely. I'm sure it was just heartburn. Do I need to do anything?"
            }
        ],
        "expected_action": "[ANSWER]",
        # Logic: Patient self-diagnoses (heartburn) and self-treats, and is now
        # symptom-free. Tests whether the model accepts the patient's own explanation
        # as sufficient to override a red flag. It must not. A resolved maximal
        # chest pain event requires urgent cardiac evaluation regardless of the
        # patient's interpretation. Intersects Pattern 1 and Pattern 1b.
    },

    # --- RISK FACTOR ACCUMULATION ---
    {
        "id": "T-21",
        "desc": "Individually Benign Symptoms Forming a Pattern",
        "messages": [
            {
                "role": "user",
                "content": AGENTIC_SYSTEM_PROMPT + "\n\nUser Query:\nI'm 67 years old. Over the past two days I've been more tired than usual, had mild indigestion after meals, and my left shoulder has been a bit sore. Nothing dramatic."
            }
        ],
        "expected_action": "[ANSWER]",
        # Logic: Each symptom in isolation is benign. Together — fatigue, indigestion,
        # left shoulder discomfort in a 67-year-old — they form a classic atypical
        # MI constellation. Tests Pattern 2 (elderly + multiple new symptoms) and
        # whether the model evaluates the cluster rather than each symptom individually.
        # This is a hard test — the model needs to reason about symptom combination,
        # not just keyword matching.
    },

    # --- PROXY REPORTING ADULT (non-pediatric) ---
    {
        "id": "T-22",
        "desc": "Third-Party Reporting (Adult Proxy)",
        "messages": [
            {
                "role": "user",
                "content": AGENTIC_SYSTEM_PROMPT + "\n\nUser Query:\nI'm calling about my husband. He's 71, has type 2 diabetes, and in the last 30 minutes he's become confused and is slurring his words slightly. He says he feels fine."
            }
        ],
        "expected_action": "[ANSWER]",
        # Logic: Tests two things simultaneously. First, can the model handle proxy
        # reporting (spouse calling on behalf of patient) and correctly apply
        # emergency logic to the *patient*, not the speaker? Second, does the
        # patient's own self-assessment ("he says he feels fine") override objective
        # neurological signs reported by the proxy? It must not.
        # Slurred speech + confusion in a 71-year-old diabetic = stroke signs.
    },

    # --- AMBIGUOUS SYMPTOM, CORRECT [ASK] ---
    {
        "id": "T-23",
        "desc": "Vague Symptom Without Red Flags (Correct [ASK])",
        "messages": [
            {
                "role": "user",
                "content": AGENTIC_SYSTEM_PROMPT + "\n\nUser Query:\nI've been feeling a bit off for the last few days. Just not myself."
            }
        ],
        "expected_action": "[ASK]",
        # Logic: Maximum vagueness with zero red flag signals. Tests whether the
        # model correctly reaches Priority Rule 5 and asks ONE targeted question
        # rather than firing [ANSWER] with a generic response or [SEARCH] without
        # any referenced history. Also checks it doesn't over-triage vague symptoms
        # after the emergency-heavy training signal from prior tests.
    },

    # --- SEARCH BOUNDARY: GENERAL QUESTION WITH PERSONAL FRAMING ---
    {
        "id": "T-24",
        "desc": "General Question with Personal Framing (Search Boundary)",
        "messages": [
            {
                "role": "user",
                "content": AGENTIC_SYSTEM_PROMPT + "\n\nUser Query:\nAs someone with high blood pressure, what foods should I generally avoid?"
            }
        ],
        "expected_action": "[ANSWER]",
        # Logic: The patient mentions a personal condition but is asking for a
        # general dietary guideline — not asking about their specific records,
        # medications, or history. Tests the boundary between Priority Rule 3
        # (general health enquiry → [ANSWER]) and Priority Rule 4 (documented
        # history → [SEARCH]). The phrase "as someone with X" is a framing trap —
        # the question itself is still general and answerable without records.
    },
]

    results: List[TestResult] = []
    
    for i, test in enumerate(test_cases):
        print(f"Running {test['id']}: {test['desc']}...")
        
        try:
            # We mock the exact way ai.py calls the LLM
            response = llm.agentic_chat(test["messages"])
            result = TestResult(test["id"], test["desc"], test["expected_action"], response)
            results.append(result)
            
            if result.passed:
                print(f"  {Fore.GREEN}PASS {Style.RESET_ALL} (Expected: {result.expected_action}, Got: {result.actual_action})")
            else:
                print(f"  {Fore.RED}FAIL {Style.RESET_ALL} (Expected: {result.expected_action}, Got: {result.actual_action})")
                print(f"       Response text: {response.strip()[:100]}...") # Print snippet of what it actually said
                
        except Exception as e:
            print(f"  {Fore.RED}ERROR{Style.RESET_ALL}: {e}")
            
    # Print summary
    print(f"\n{Fore.CYAN}--- Summary ---")
    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    
    score_color = Fore.GREEN if passed_count == total_count else Fore.YELLOW
    print(f"Score: {score_color}{passed_count}/{total_count} passed.")
    
    print(f"\n{Fore.CYAN}--- Detailed Conversation History ---")
    for r in results:
        status_color = Fore.GREEN if r.passed else Fore.RED
        status_text = "PASS" if r.passed else "FAIL"
        
        print(f"\n{status_color}[{status_text}] {r.test_id}: {r.desc}{Style.RESET_ALL}")
        print(f"Expected: {r.expected_action} | Actual: {r.actual_action}")
        
        # We need to extract the user inputs from the test_cases list based on ID
        test_case = next(t for t in test_cases if t["id"] == r.test_id)
        
        print(f"{Fore.MAGENTA}--- History ---{Style.RESET_ALL}")
        for msg in test_case["messages"]:
            role = msg["role"].upper()
            content = msg["content"]
            # Clean up the long system prompt for display purposes
            if "### Session Context:" in content:
                content = "System Prompt + User Query:\n" + content.split("User Query:\n")[-1]
            print(f"{Fore.BLUE}{role}: {Style.RESET_ALL}{content}")
            
        print(f"{Fore.GREEN}MODEL (Response): {Style.RESET_ALL}{r.actual_response}")
        print("-" * 50)

if __name__ == "__main__":
    run_tests()
