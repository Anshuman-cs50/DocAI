# DocAI: Agentic Medical Consultation Assistant

DocAI is a sophisticated, privacy-focused medical consultation system. It replaces naive static RAG (Retrieval-Augmented Generation) with a **dynamic ReAct Agent architecture**, utilizing Google's medically-tuned `MedGemma-4b` model to interact with patients and autonomously query their historical health records.

## 🚀 Key Features

* **Autonomous ReAct LLM Agent:** The core consultation loop is agentic. The AI evaluates the conversation natively and decides whether to `[SEARCH]` the patient's medical history for context, or `[ANSWER]` the user directly, minimizing hallucinations.
* **Semantic Health Record Search:** Integrates **pgvector** and a locally hosted **BioBERT** embedding model to perform high-speed, semantic similarity searches across a user's consultation summaries and clinical notes.
* **Native Multi-Modal Message History:** Context is passed to the LLM as structured HuggingFace-compliant Chat Template arrays, preserving the true conversational turns.
* **Decoupled Backend Architecture:** Runs the heavy 4-Billion parameter MedGemma model on Kaggle's free GPU tier via an automated Gradio tunnel, keeping the local Flask server lightweight and blazing fast.
* **One-Click Startup Automation:** Features a robust Powershell script (`start.ps1`) to spin up PostgreSQL, apply database schemas, launch the Flask UI, and establish ngrok tunnels automatically.

## 🏗️ Architecture Stack

* **Backend Framework:** Python / Flask
* **Database:** PostgreSQL with `pgvector` extension
* **Embedding Model:** `pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb` (768D)
* **Agentic Reasoning LLM:** `google/medgemma-4b-it` (Hosted off-device via Kaggle+Gradio)
* **Background Processing LLM:** `Qwen/Qwen2.5-7B-Instruct` (via HuggingFace Inference API)

## 📁 Project Structure

```text
DocAI/
├── ai/                     # Core Agentic Intelligence Logic
│   ├── ai.py               # Orchestrates the ReAct [SEARCH]/[ANSWER] loops
│   ├── embedding.py        # Generates BioBERT vector embeddings
│   ├── LLM_module.py       # Interfaces with HuggingFace/Gradio & houses strict Prompts
│   └── MemoryManager.py    # Standardizes Message arrays for history tracking
├── app/                    # Flask Web Application
│   ├── routes.py           # API Endpoints (/consult, /update_gradio_url)
│   └── __init__.py         # App factory & config
├── db/                     # Database schemas and CRUD operations
├── notebooks/              
│   └── kaggle_host.py      # The Kaggle notebook to host the GPU LLM tunnel
├── .env                    # Secrets (HF Token, Ngrok Token, etc)
├── start.ps1               # Automated Docker & Flask bootstrapper
└── run.py                  # Entry point
```

## ⚙️ Setup and Installation

### 1. Requirements
* Docker Desktop (for Postgres/pgvector)
* Python 3.10+
* A free [Ngrok](https://ngrok.com/) Account
* A free [HuggingFace](https://huggingface.co/) Account (with user access token)
* A [Kaggle](https://www.kaggle.com/) Account (for free GPU hosting)

### 2. Environment Configuration
Create a `.env` file in the root directory:
```env
# Database Configuration
DB_HOST=127.0.0.1
DB_PORT=5432
DB_USER=root
DB_PASSWORD=root
DB_NAME=docbase

# HuggingFace & Kaggle Configuration
HF_API_TOKEN=your_hf_access_token
URL_UPDATE_SECRET=docai-url-push-secret
```

### 3. Launch the Backend
Simply run the robust startup script from PowerShell. It will boot Docker, initialize pgvector, install python dependencies, and launch Flask.
```powershell
.\start.ps1
```

### 4. Boot the AI Brain (Kaggle)
1. Upload `notebooks/kaggle_host.py` to a new Kaggle Notebook.
2. Ensure the "T4 x2" (or better) GPU accelerator is active.
3. Add your `HF_TOKEN`, `DOCAI_SERVER_URL` (the ngrok url printed out by `start.ps1`), and `DOCAI_SECRET` (matching your `.env`) to the Kaggle Secrets tab.
4. Run all cells. The notebook will host MedGemma-4b on Kaggle's GPU and automatically inform your local Flask server of the secure tunnel address.

### 5. Chat!
Your DocAI system is now fully synced, agentic, and ready to respond to complex medical queries while searching semantic history.

---

> **Disclaimer:** DocAI is a theoretical software project. It is **not** a certified medical device and should not be used to replace professional clinical judgment or offer definitive medical diagnoses.