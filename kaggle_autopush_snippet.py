# =============================================================================
# DocAI — Kaggle Auto-Push Snippet
#
# Paste this as the LAST cell of your Kaggle notebook, after the Gradio
# interface has launched. It automatically pushes the new URL to your
# local Flask server so you never have to copy-paste it manually.
#
# SETUP (one-time):
#   1. Set DOCAI_SERVER_URL to your Flask server's public address.
#      If you're using ngrok, this will look like https://xxxx.ngrok-free.app
#      If you're on a LAN, use your machine's local IP, e.g. http://192.168.x.x:5000
#   2. Set DOCAI_SECRET to the value of URL_UPDATE_SECRET in your .env file.
#      Default is: docai-url-push-secret
# =============================================================================

import requests
import time

# ── CONFIGURE THESE ──────────────────────────────────────────────────────────
DOCAI_SERVER_URL = "http://<YOUR_LOCAL_IP_OR_NGROK_URL>:5000"  # e.g. http://192.168.1.10:5000
DOCAI_SECRET     = "docai-url-push-secret"                     # must match URL_UPDATE_SECRET in .env
# ─────────────────────────────────────────────────────────────────────────────


def push_gradio_url_to_flask(gradio_url: str, retries: int = 3, delay: int = 5):
    """
    Pushes the Gradio URL to the running Flask server.
    Retries a few times in case the Gradio interface isn't fully live yet.
    """
    endpoint = f"{DOCAI_SERVER_URL}/update_gradio_url"
    payload  = {"url": gradio_url, "secret": DOCAI_SECRET}

    for attempt in range(1, retries + 1):
        try:
            print(f"[Attempt {attempt}/{retries}] Pushing URL to Flask: {gradio_url}")
            response = requests.post(endpoint, json=payload, timeout=15)

            if response.status_code == 200:
                print(f"✅ Flask server updated successfully! URL: {gradio_url}")
                return True
            else:
                print(f"⚠️  Server responded with {response.status_code}: {response.text}")

        except requests.ConnectionError:
            print(f"⚠️  Could not reach Flask server at {DOCAI_SERVER_URL}. Is it running?")
        except Exception as e:
            print(f"⚠️  Error: {e}")

        if attempt < retries:
            print(f"   Retrying in {delay}s...")
            time.sleep(delay)

    print("❌ Failed to push URL after all retries. Please update GRADIO_API_URL in .env manually.")
    return False


# ── USAGE ─────────────────────────────────────────────────────────────────────
# Replace the string below with the Gradio share URL printed by gr.launch()
# Or capture it programmatically from the Gradio launch output.
#
# Example (manual):
#   GRADIO_URL = "https://xxxx.gradio.live"
#   push_gradio_url_to_flask(GRADIO_URL)
#
# Example (automatic — if you capture Gradio's share_url):
#   demo, _, share_url = gr.Interface(...).launch(share=True, prevent_thread_lock=True)
#   push_gradio_url_to_flask(share_url)
