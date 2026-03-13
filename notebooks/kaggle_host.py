"""
docai — Kaggle Hosting Script
==============================
Run each cell top-to-bottom in your Kaggle notebook.

Required Kaggle Secrets (Add-ons > Secrets):
  HF_TOKEN         — HuggingFace user access token
  DOCAI_SERVER_URL — ngrok URL of your local Flask server (from start.ps1)
  DOCAI_SECRET     — must match URL_UPDATE_SECRET in your local .env

Workflow:
  1. Install deps      4. Define inference fn
  2. HF login          5. Build Gradio interface
  3. Load MedGemma     6. Launch + push URL to Flask
"""

# %% ── STEP 1: Install dependencies ─────────────────────────────────────────
# Cell 1 — no pyngrok needed; Gradio's share=True provides the public tunnel
!pip install --quiet torch torchvision torchaudio transformers accelerate gradio -q

# %% ── STEP 2: HuggingFace login via Kaggle Secrets ─────────────────────────
# Cell 2
from kaggle_secrets import UserSecretsClient
from huggingface_hub import login

secrets = UserSecretsClient()
hf_token = secrets.get_secret("HF_TOKEN")
login(token=hf_token)
print("[OK] Logged in to HuggingFace.")

# %% ── STEP 3: Load MedGemma model ──────────────────────────────────────────
# Cell 3
from transformers import pipeline
import torch

MODEL_ID = "google/medgemma-4b-it"

pipe = pipeline(
    "image-text-to-text",
    model=MODEL_ID,
    dtype=torch.bfloat16,
    device_map="auto",
)

print("[OK] MedGemma model loaded.")

# %% ── STEP 4: Define inference function ────────────────────────────────────
# Cell 4
import traceback

def medgemma_infer(text_prompt: str):
    """
    Text-only handler for MedGemma.
    Accepts a plain text prompt, returns a safe and readable response.
    Handles empty input and runtime errors gracefully.
    """
    try:
        if not text_prompt or text_prompt.strip() == "":
            return "[ERROR] Please enter a valid text prompt."

        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": text_prompt}]
            }
        ]

        output_text = pipe(
            text=messages,
            max_new_tokens=1024,
            do_sample=False
        )
        return output_text[0]["generated_text"][1]["content"]

    except torch.cuda.OutOfMemoryError:
        return "[ERROR] GPU memory exhausted. Restart the runtime or use a shorter prompt."

    except Exception as e:
        return f"[ERROR] Inference failed: {str(e)}\n\nTraceback:\n{traceback.format_exc(limit=1)}"

print("[OK] Inference function defined.")

# %% ── STEP 5: Build Gradio interface ───────────────────────────────────────
# Cell 5
import gradio as gr

iface = gr.Interface(
    fn=medgemma_infer,
    inputs=[
        gr.Textbox(
            label="Enter your medical prompt",
            lines=2,
            placeholder="Type here..."
        ),
    ],
    outputs=gr.Markdown(label="Output"),
    title="MedGemma - Medical AI Assistant",
    theme="gradio/soft",
)

print("[OK] Gradio interface built.")

# %% ── STEP 6: Launch Gradio with built-in share tunnel ─────────────────────
# Cell 6
# Uses Gradio's own share tunnel (gradio.live) — NOT ngrok.
# This avoids the ngrok "1 session limit" error since your local machine
# already uses ngrok to expose Flask.
#
# prevent_thread_lock=True lets the next cell run immediately after launch.

_, _, share_url = iface.launch(
    server_name="0.0.0.0",
    server_port=7860,
    share=True,
    prevent_thread_lock=True,
    quiet=True
)

PUBLIC_URL = share_url
print(f"[OK] Gradio live at: {PUBLIC_URL}")
print("[STEP] URL will be pushed to Flask in Step 7.")

# %% ── STEP 7: Auto-push URL to local DocAI Flask server ────────────────────
# Cell 7
# REQUIRED SECRETS (add in the Kaggle Secrets panel):
#   DOCAI_SERVER_URL  — your local Flask server's public address via ngrok
#                       e.g. https://xxxx.ngrok-free.app
#   DOCAI_SECRET      — must match URL_UPDATE_SECRET in your local .env
#                       default: docai-url-push-secret
import requests
import time

DOCAI_SERVER_URL = secrets.get_secret("DOCAI_SERVER_URL")
DOCAI_SECRET     = secrets.get_secret("DOCAI_SECRET")

def push_gradio_url_to_flask(gradio_url: str, retries: int = 4, delay: int = 5):
    """Pushes the live Gradio URL to the running Flask server with retry logic."""
    endpoint = f"{DOCAI_SERVER_URL.rstrip('/')}/update_gradio_url"
    payload  = {"url": gradio_url, "secret": DOCAI_SECRET}

    for attempt in range(1, retries + 1):
        try:
            print(f"[STEP] Attempt {attempt}/{retries} — pushing URL to Flask...")
            response = requests.post(endpoint, json=payload, timeout=15)

            if response.status_code == 200:
                print(f"[OK] Flask updated!")
                print(f"     Gradio URL : {gradio_url}")
                print(f"     Flask host : {DOCAI_SERVER_URL}")
                return True
            elif response.status_code == 401:
                print("[ERROR] Auth failed — DOCAI_SECRET does not match URL_UPDATE_SECRET in .env")
                return False
            else:
                print(f"[WARN] Server responded {response.status_code}: {response.text[:120]}")

        except requests.ConnectionError:
            print(f"[WARN] Cannot reach Flask at {DOCAI_SERVER_URL} — is start.ps1 running?")
        except Exception as e:
            print(f"[WARN] Unexpected error: {e}")

        if attempt < retries:
            print(f"       Retrying in {delay}s...")
            time.sleep(delay)

    print("[ERROR] Could not push URL to Flask after all retries.")
    print(f"        Manual fallback:")
    print(f'        curl -X POST "{DOCAI_SERVER_URL}/update_gradio_url" -H "Content-Type: application/json" -d \'{{"url":"{gradio_url}","secret":"<your-secret>"}}\'')
    return False


# Give Gradio 3 seconds to fully bind before pushing
time.sleep(3)
push_gradio_url_to_flask(PUBLIC_URL)
