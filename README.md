# 🚀 AI-Qgen | Technical Overview

**AI-Qgen** is a bilingual question generation engine that transforms static PDFs into dynamic, structured exam banks. It uses a **RAG (Retrieval-Augmented Generation)** architecture to handle massive documents on low-end hardware.

---

## 🛠️ Tech Stack
*   **Backend**: FastAPI (Python 3.10+)
*   **Database**: PostgreSQL (Metadata) & ChromaDB (Vector Embeddings)
*   **AI Engine**: Ollama (Local) & Groq (Cloud)
*   **PDF Engine**: PyMuPDF (fitz)
*   **Frontend**: Vanilla HTML5, CSS3, JavaScript

---

## 🏗️ System Architecture
#PDF_Extraction ➔ #Vector_Indexing ➔ #RAG_Retrieval ➔ #LLM_Generation ➔ #Bilingual_Transformation

### 📂 File Structure & Responsibilities
*   **`backend/main.py`**: The application heart. Configures FastAPI, CORS, and mounts the API routers.
*   **`backend/routers.py`**: The orchestrator. Handles HTTP requests and manages the flow between PDF extraction, Vector storage, and AI generation.
*   **`backend/models.py`**: Defines the SQL schema for Subjects, Questions, and Papers using SQLAlchemy.
*   **`backend/services/pdf_extractor.py`**: High-efficiency PDF parser. Uses iterative streaming to handle 400+ pages without RAM spikes.
*   **`backend/services/vector_db.py`**: Manages the **ChromaDB** instance. Handles persistent storage and semantic similarity search.
*   **`backend/services/llm_service.py`**: The AI logic. Formulates RAG prompts and manages bilingual output (English/Hindi) using Ollama/Groq.
*   **`backend/services/paper_generator.py`**: Selects and filters questions from the database to build a balanced exam paper.
*   **`backend/services/exporter.py`**: Converts structured JSON data into professional Microsoft Word (`.docx`) files.

---

## 🔄 The Data Transformation Workflow

### 1. Ingestion Strategy (#Chunking)
When a PDF is uploaded, the text is not stored as one giant block. It is broken into **Semantic Chunks** (approx. 1500 characters) with a **15% overlap**. This overlap ensures that concepts split across two pages are not lost.

### 2. Retrieval Strategy (#Retriever)
Instead of the AI reading the whole book, the system performs a **Vector Search**:
- **Query**: "Generate MCQ about Photosynthesis."
- **Search**: ChromaDB finds the top 3 most relevant chunks of text using the `all-MiniLM-L6-v2` embedding model.
- **Result**: Only those specific pages are sent to the AI.

### 3. Generation Strategy (#LLM)
The system uses a **Bilingual Prompting** strategy:
- **Input**: Context Chunks + Strict JSON Schema.
- **Transformation**: The model processes the English context and generates a pair: `{question_en, question_hi}`.
- **Strictness**: Options for MCQs are enforced in `English / Hindi` format to ensure readability for all students.

---

## 🚀 Quick Setup Guide

### 1️⃣ Environment
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install --no-cache-dir -r requirements.txt
```

### 2️⃣ Configuration
Update your `.env` with:
```env
DATABASE_URL="postgresql://user:pass@localhost:5432/ai_qgen"
USE_OLLAMA=True
OLLAMA_MODEL=qwen2.5:3b
```

### 3️⃣ Run
*   **Backend**: `uvicorn backend.main:app --reload`
*   **Frontend**: `python -m http.server 3000 --directory frontend`

---
*Optimized for 8GB RAM | Powered by RAG & ChromaDB*
