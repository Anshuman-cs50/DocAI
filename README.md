# DocAI: Agentic Medical Consultation Assistant

DocAI is a sophisticated, privacy-focused medical consultation system. It replaces naive static RAG (Retrieval-Augmented Generation) with a **dynamic ReAct Agent architecture**, utilizing Google's medically-tuned `MedGemma-4b` model to interact with patients and autonomously query their historical health records.

## 🚀 Key Features

* **Autonomous ReAct LLM Agent:** The core consultation loop is agentic. The AI evaluates the conversation natively and decides whether to `[SEARCH]` the patient's medical history for context, or `[ANSWER]` the user directly, minimizing hallucinations.
* **Semantic Health Record Search:** Integrates **pgvector** and a locally hosted **BioBERT** embedding model to perform high-speed, semantic similarity searches across a user's consultation summaries and clinical notes.
* **Event-Driven Memory Pipeline:** Automates background insight extraction, summarization, and active condition detection asynchronously when a consultation ends, keeping the UI blazing fast.
* **Decoupled Backend Architecture:** Runs the heavy 4-Billion parameter MedGemma model on Kaggle's free GPU tier via an automated Gradio tunnel, keeping the local Flask server lightweight.
* **Modern React Frontend:** Built with Vite and TailwindCSS for a responsive, dynamic user experience.


## 🏗️ Architecture Stack
 
* **Frontend Framework:** React (Vite) + TailwindCSS
* **Backend Framework:** Python / Flask
* **Database:** PostgreSQL with `pgvector` extension
* **Embedding Model:** `pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb` (768D)
* **Agentic Reasoning LLM:** `google/medgemma-4b-it` (Hosted off-device via Kaggle+Gradio)
* **Background Processing LLM:** `Qwen/Qwen2.5-7B-Instruct` (via HuggingFace Inference API)

## 📁 Project Structure

```text
DocAI/
├── backend/                    # Python / Flask API Server
│   ├── run.py                  # Entry point (python run.py)
│   ├── requirements.txt        # Python dependencies
│   ├── render.yaml             # Render.com deployment config
│   ├── .env                    # Secrets (not committed)
│   ├── app/                    # Flask application
│   │   ├── routes.py           # API endpoints (/consult, /signup, /login, ...)
│   │   └── __init__.py         # App factory & config
│   ├── ai/                     # Core Agentic Intelligence Logic
│   │   ├── ai.py               # Orchestrates the ReAct [SEARCH]/[ANSWER] loops
│   │   ├── embedding.py        # Generates BioBERT vector embeddings
│   │   ├── LLM_module.py       # HuggingFace/Gradio interfaces & prompts
│   │   ├── post_processing.py  # Background memory & summarization pipeline
│   │   ├── UserConditionManager.py # Autonomous diagnosis state machine
│   │   └── MemoryManager.py    # Message history management
│   └── db/                     # Database schemas and CRUD operations
│       ├── database.py         # SQLAlchemy session & URI config
│       ├── models.py           # ORM models
│       └── crud.py             # Database operations
└── frontend/                   # React (Vite) User Interface
    ├── src/                    # React components & pages
    ├── vite.config.js          # Vite config (includes /api proxy for dev)
    ├── .env.example            # Document env vars for production
    └── package.json
```

## ⚙️ Setup and Installation

### Requirements
* Node.js and npm (for the React frontend)
* Docker Desktop (for Postgres/pgvector)
* Python 3.10+
* A free [HuggingFace](https://huggingface.co/) account (with user access token)
* A [Kaggle](https://www.kaggle.com/) account (for free GPU hosting)

---

### Backend Setup

```powershell
cd backend

# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
# Copy .env.example to .env and fill in your values:
# DATABASE_URI, HF_API_TOKEN, URL_UPDATE_SECRET
```

Create `backend/.env`:
```env
DATABASE_URI=postgresql://user:password@localhost:5432/DocAI
HF_API_TOKEN=your_hf_access_token
URL_UPDATE_SECRET=docai-url-push-secret
SECRET_KEY=your-secret-key
```

```powershell
# 4. Run the Flask API server (default: http://localhost:5000)
python run.py
```

---

### Frontend Setup

```powershell
cd frontend

# 1. Install dependencies
npm install

# 2. Start the dev server (default: http://localhost:5173)
#    API calls to /api/* are automatically proxied to http://localhost:5000
npm run dev
```

For **production**, copy `frontend/.env.example` to `frontend/.env.local` and set:
```env
VITE_API_BASE_URL=https://your-backend.onrender.com
```

---

### Boot the AI Brain (Kaggle)
1. Upload a Kaggle Notebook running the DocAI Inference server.
2. Ensure the "T4 x2" (or better) GPU accelerator is active.
3. Add your `HF_TOKEN`, `DOCAI_SERVER_URL` (your deployed backend URL), and `DOCAI_SECRET` (matching `URL_UPDATE_SECRET` in `.env`) to Kaggle Secrets.
4. Run all cells. The notebook hosts MedGemma-4b on Kaggle's GPU and automatically pushes the tunnel URL to your backend.

---

> **Disclaimer:** DocAI is a theoretical software project. It is **not** a certified medical device and should not be used to replace professional clinical judgment or offer definitive medical diagnoses.
