# AI_Qgen | Bilingual AI Exams

Welcome to **AI_Qgen**! This system provides highly dynamic, bilingual (English/Hindi) question bank generation from context (PDFs) and a dynamic question paper assembly system.

---

## 🛠 Setup & Installation

Follow these steps to set up the project on your local machine.

### 1. Prerequisites

- **Python**: 3.10 or higher.
- **PostgreSQL**: Ensure a local instance is running or have a Supabase URL ready.
- **Ollama (Optional)**: If you wish to run models locally instead of using Groq Cloud.

### 2. Installation

1. **Clone the Repository**:
   ```bash
   git clone [your-repo-link]
   cd AI_Qgen_Main_offline
   ```
2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Environment Configuration

Create a `.env` file in the root directory and add your credentials:

```env
DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@localhost:5432/ai_qgen"
GROQ_API_KEY="your_gsk_key_here"

# --- Optional Local AI ---
USE_OLLAMA=True
OLLAMA_MODEL=dolphin3:latest
```

### 4. Database Initialization

This project uses **Alembic** for schema management. Run this to create the tables:

```bash
alembic upgrade head
```

---

## 🚀 Running the Project

### 1. Start the Backend (FastAPI)

```bash
uvicorn backend.main:app --reload --port 8000
```

- The API will be available at `http://localhost:8000`.
- Documentation (Swagger) is available at `http://localhost:8000/docs`.

### 2. Start the Frontend

Since the dashboard is built with vanilla HTML/JS, you can open `frontend/index.html` directly or serve it via Python:

```bash
cd frontend
python -m http.server 3000
```

Then navigate to `http://localhost:3000`.

or 

`python -m http.server 3000 --directory frontend`

---

## ⚠️ Troubleshooting: The 'exam_type' Error

If you (or a colleague) encounter an error like:
`psycopg2.errors.UndefinedColumn: column "exam_type" of relation "examinations" does not exist`

This means your local database schema is out of sync with the latest code updates.

### Solution 1: The Alembic Way (Recommended)

Run the latest migrations to auto-fix the schema:

```bash
alembic upgrade head
```

### Solution 2: The Manual Fix Script

If you are unable to run migrations, we provide a standalone fix script:

1. Ensure your `.env` has the correct `DATABASE_URL`.
2. Run the utility script:
   ```bash
   python migrate_db.py
   ```

This script will safely check for missing columns (like `exam_type`) and add them to your database without deleting any of your existing data.

---

## 🔄 How to Switch Databases (Local vs Supabase)

The system supports **Hot-Swapping Database Connections** via the UI:

1. Click **⚙️ Settings** in the Navbar.
2. Paste your new `postgresql://` connection string.
3. Click **Save**. The backend will overwrite your `.env` and immediately switch the active connection without a restart.

---

## 📄 How to Use

- **Part A (Generator)**: Register a subject, upload a PDF syllabus, and use the **+ Add Type** button to define how many questions you want the AI to generate.
- **Part B (Assembler)**: Use the "Create Question Paper" section to build sections, define "Attempt Any" rules, and fetch questions from the pool to compile a professional `.docx` paper.
