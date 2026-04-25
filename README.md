# 📝 AI-Qgen | Question Bank Manager & Exam Generator

**AI-Qgen** has evolved into a robust, high-performance system for managing legacy question banks and generating professional university-grade examination papers. It completely bypasses complex AI generation in favor of a reliable, human-curated **Bulk CSV Import** pipeline.

---

## 🏗️ System Architecture
The application is built on a lightweight, decoupled architecture optimized for speed and reliability.

### 🛠️ Tech Stack
*   **Backend**: FastAPI (Python 3.11+)
*   **Database**: PostgreSQL (Relational Data)
*   **ORM & Migrations**: SQLAlchemy & Alembic
*   **Frontend**: Vanilla HTML5, CSS3, JavaScript
*   **Document Generation**: `python-docx`

### 📂 File Structure & Responsibilities
*   **`backend/main.py`**: The application heart. Configures FastAPI, CORS, and auto-generates tables if missing.
*   **`backend/routers.py`**: The orchestrator. Handles HTTP requests for Subject management, CSV parsing, and Paper generation.
*   **`backend/models.py`**: Defines the SQL schema for Subjects, Questions, Examinations, and Papers.
*   **`backend/services/paper_generator.py`**: The selection engine. Uses intelligent anti-repetition logic (`usage_count`) to select fresh questions for every new exam.
*   **`backend/services/exporter.py`**: The formatting engine. Converts selected questions into perfectly formatted Microsoft Word (`.docx`) files with official headers, watermarks, and bilingual layouts.

---

## 🔄 How It Works

The system operates on a streamlined 3-step workflow:

### 1. 📚 Subject Registration
Users create a "bucket" for their questions by registering a Subject (e.g., *Software Engineering, CS-501*).

### 2. 📥 Bulk CSV Import
Teachers or administrators format their legacy question banks using the system's strict CSV template. 
*   **Bilingual Fallback:** If Hindi translations are missing, the backend automatically injects `[Hindi Missing]` to preserve the layout structure.
*   **JSON Packing:** Multiple choice options (A, B, C, D) are automatically serialized into a single JSON column in PostgreSQL to maintain schema cleanliness.

### 3. 📝 Exam Generation
When an exam is requested, the system:
1. Queries the PostgreSQL database for the specific subject.
2. Filters out questions that have been used recently.
3. Randomly selects the required number of questions per section.
4. Updates the `usage_count` so those questions aren't repeated in the next exam.
5. Generates a `.docx` file and Answer Key.

---

## 🚀 Quick Setup Guide

### 1️⃣ Environment Setup
Create a virtual environment and install the lightweight dependencies:
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2️⃣ Database Configuration
Create a `.env` file in the root directory and add your PostgreSQL credentials:
```env
DATABASE_URL="postgresql://postgres:yourpassword@localhost:5432/ai_qgen"
```

### 3️⃣ Run Database Migrations (Alembic)
To ensure your PostgreSQL database schema is perfectly synced with the models:
```powershell
# Create the initial tables and apply migrations
alembic upgrade head
```
*(Note: `main.py` also contains a fallback to auto-create tables if Alembic is bypassed for quick local testing).*

### 4️⃣ Run the Application
You will need two terminals to run the system:

**Terminal 1 (Backend):**
```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 (Frontend):**
```powershell
cd frontend
python -m http.server 3000
```

Open your browser to `http://localhost:3000` to access the dashboard!
