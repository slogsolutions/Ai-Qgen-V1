# AI_Qgen | Bilingual AI Exams

Welcome to the **AI_Qgen** project! This system provides highly dynamic, bilingual (English/Hindi) question bank generation from context (PDFs) and a dynamic question paper assembly system.

## Starting the Project

### 1. Requirements 
Ensure you have Python and PostgreSQL installed locally. 
- Python 3.10+
- `pip install -r requirements.txt` (Assuming dependencies like FastAPI, Uvicorn, SQLAlchemy, psycopg2, python-docx, groq, httpx)

### 2. Run the Backend
Start the FastAPI server via Uvicorn.
```bash
cd backend
uvicorn app:app --reload --port 8000
```
*(Optionally setup your `.env` file containing `DATABASE_URL` and `GROQ_API_KEY` in the project root).*

### 3. Run the Frontend 
Since this is a vanilla HTML/JS dashboard, you can open `frontend/index.html` directly in your browser or run a simple local web server:
```bash
cd frontend
python -m http.server 8080
```
Then navigate to `http://localhost:8080` in your web browser.

---

## How to Switch Databases (Local vs Supabase)

The system is equipped with **Hot-Swapping Database Connections**. This means you do not have to stop your backend completely to switch between offline development and online cloud deployments.

**Local PostgreSQL Format**: 
`postgresql://postgres:YOUR_PASSWORD@localhost:5432/YOUR_DB_NAME`

**Supabase Format**: 
`postgresql://postgres.your_project:[YOUR-PASSWORD]@aws-0-REGION.pooler.supabase.com:6543/postgres`

### Switching via the UI Dashboard
1. Open the frontend dashboard `index.html`.
2. On the Top Navigation Bar, click **⚙️ Settings**.
3. A modal will pop up. Paste your new `postgresql://` connection string into the input box.
4. Click **"Save Configurations"**.
5. The backend immediately overwrites your local `.env` and safely hot-swaps the active SQLAlchemy engine in real-time. All subsequent database reads/writes will hit the newly provided database.

---

## How to Use the Generator

### Part A: Generate New Question Bank (AI)
1. Provide **Subject Metadata** to register your current exam.
2. Under "Generate New Question Bank", specify the subject and upload a **Syllabus PDF**.
3. **Question Requirements**: Click **+ Add Type** to define exact formats (e.g., 5 MCQ, 10 Fill-in-the-Blanks).
4. **Difficulty**: Pick from Easy, Medium, Hard. The AI will strictly follow this scale.
5. Hit generation. The system splits the PDF and enforces numeric constraints effectively, populating the database.

### Part B: Create Question Paper (Print Format)
1. Proceed down to "Create Question Paper".
2. **Dynamic Sections Builder**: You can add sections like "Section A". For each section, provide:
   - *Attempt Any (X) / Total*: The amount of questions a student must do (used for calculating points)
   - *Marks per Q*: Individual point value.
3. Click **+ Add Specific Type Request** to formulate question pools inside the section. (e.g. telling it to pull 5 MCQs and 3 True/False questions directly into Section A).
4. Compile the paper! The Engine securely groups them up, calculates the section's total points dynamically, and triggers a `.docx` download alongside a translated `.docx` Answer Key automatically.
