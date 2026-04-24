from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from sqlalchemy.orm import Session
from typing import Optional
from .database import get_db, update_engine
from . import schemas, models
from .services import pdf_extractor, llm_service, paper_generator, exporter, model_fetcher
import json
import os
import re
import datetime
import random
import csv
import io
router = APIRouter()

@router.post("/subjects/", response_model=schemas.SubjectResponse)
def create_subject(subject: schemas.SubjectCreate, db: Session = Depends(get_db)):
    db_subject = models.Subject(**subject.dict())
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    return db_subject

@router.get("/subjects/", response_model=list[schemas.SubjectResponse])
def get_subjects(db: Session = Depends(get_db)):
    return db.query(models.Subject).all()

@router.post("/settings/")
def update_settings(db_url: str = Body(...)):
    """Update DATABASE_URL dynamically"""
    try:
        env_path = ".env"
        # extremely simple approach for a demonstration env
        content = ""
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                content = f.read()
                
        if "DATABASE_URL=" in content:
            content = re.sub(r'DATABASE_URL=.*', f'DATABASE_URL="{db_url}"', content)
        else:
            content += f'\nDATABASE_URL="{db_url}"\n'
            
        with open(env_path, "w") as f:
            f.write(content)
            
        update_engine(db_url)
        # We might also need to set os.environ so getenv works correctly
        os.environ["DATABASE_URL"] = db_url
        return {"message": "Database configuration updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/llm/models/")
def get_llm_models(provider: str = "groq"):
    """Returns available models for the given provider."""
    if provider == "ollama":
        return model_fetcher.get_ollama_models()
    elif provider == "gemini":
        return model_fetcher.get_gemini_models()
    return model_fetcher.get_groq_models()

@router.post("/generate/from-pdf/")
async def generate_from_pdf(
    subject_id: int, 
    file: Optional[UploadFile] = File(None), 
    q_types_config: str = Form("[]"),
    difficulty: str = Form("Medium"),
    provider: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    import asyncio
    from .services import vector_db
    
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Check if we can reuse existing pool
    should_reindex = True
    
    if file:
        if subject.last_syllabus_filename == file.filename:
            if not vector_db.is_collection_empty(subject_id):
                should_reindex = False
                print(f"[{datetime.datetime.now()}] Skipping extraction/indexing: Found existing pool for '{file.filename}'")
        
        if should_reindex:
            # 1. Extract and chunk PDF
            print(f"[{datetime.datetime.now()}] 1/3: Extracting and chunking PDF... (this may take a few seconds)")
            chunks = await pdf_extractor.extract_and_chunk_pdf(file)
            print(f"[{datetime.datetime.now()}] Extracted {len(chunks)} text chunks.")
            
            # 2. Store in Vector DB
            print(f"[{datetime.datetime.now()}] 2/3: Storing chunks in Vector Database...")
            await asyncio.to_thread(vector_db.store_chunks, subject_id, chunks)
            print(f"[{datetime.datetime.now()}] Vector indexing complete.")
            
            # Update last filename in DB
            subject.last_syllabus_filename = file.filename
            db.commit()
    else:
        # No file provided, check if pool exists
        if vector_db.is_collection_empty(subject_id):
            raise HTTPException(status_code=400, detail="No syllabus provided and no existing pool found for this subject.")
        print(f"[{datetime.datetime.now()}] Using existing vector pool for subject {subject_id}")
    
    try:
        types_config = json.loads(q_types_config)
    except Exception:
        types_config = []

    type_limits = {}
    total_requested = 0
    for tc in types_config:
        qt = tc.get("q_type", "Mixed")
        nq = int(tc.get("num_q", 0))
        
        # Enforce backend limit of 300 questions per type
        if nq > 300:
            nq = 300
            
        if nq > 0:
            type_limits[qt] = type_limits.get(qt, 0) + nq
            total_requested += nq
            
    # Enforce global backend limit of 300 questions total per request
    if total_requested > 300:
        raise HTTPException(status_code=400, detail="Backend Limit Exceeded: You cannot generate more than 300 questions at a time.")

    try:
        # If ollama selected, ensure it's serving
        if provider == "ollama":
            model_fetcher.ensure_ollama_running()
            
        # 3. Generate questions using RAG via asyncio.to_thread to prevent blocking event loop
        print(f"[{datetime.datetime.now()}] 3/3: Asking AI to generate questions. This is the heavy lifting part and may take several minutes depending on hardware...")
        generated = await asyncio.to_thread(
            llm_service.generate_questions_rag,
            subject_id=subject_id,
            types_config=types_config,
            difficulty=difficulty,
            provider=provider,
            model=model_name
        )
        print(f"[{datetime.datetime.now()}] AI Generation finished! Saving to database...")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    saved_qs = []
    type_counts = {}
    
    for q_data in generated:
        if not isinstance(q_data, dict):
            continue
            
        actual_q_type = q_data.get("q_type", "Mixed")
        
        if type_limits:
            # If "Mixed" quota exists, allow any valid type to consume it
            if "Mixed" in type_limits and type_limits["Mixed"] > 0:
                current_mixed = type_counts.get("Mixed", 0)
                if current_mixed < type_limits["Mixed"]:
                    type_counts["Mixed"] = current_mixed + 1
                else:
                    continue
            else:
                current_count = type_counts.get(actual_q_type, 0)
                limit = type_limits.get(actual_q_type, 0)
                
                if limit <= 0 or current_count >= limit:
                    continue 
                    
                type_counts[actual_q_type] = current_count + 1

        options_json = json.dumps(q_data.get("options")) if q_data.get("options") else None

        q_en = str(q_data.get("question_en", ""))
        q_hi = str(q_data.get("question_hi", ""))
        
        if actual_q_type == "T/F":
            if "True / False" not in q_en:
                q_en = q_en.strip() + " [True / False]"
            if "सही / गलत" not in q_hi:
                q_hi = q_hi.strip() + " [सही / गलत]"

        new_q = models.Question(
            subject_id=int(subject_id),
            q_type=str(actual_q_type),
            difficulty=str(difficulty),
            question_en=q_en,
            question_hi=q_hi,
            answer_en=str(q_data.get("answer_en", "")),
            answer_hi=str(q_data.get("answer_hi", "")),
            options=options_json
        )
        db.add(new_q)
        saved_qs.append(new_q)
        
    db.commit()
    return {"message": f"Generated {len(saved_qs)} questions successfully."}

@router.post("/import-csv/subject/{subject_id}")
async def import_csv_questions(subject_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Imports questions directly from a structured CSV file."""
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")

    content = await file.read()
    try:
        decoded_content = content.decode('utf-8-sig') # utf-8-sig removes BOM if present
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV file must be UTF-8 encoded.")

    csv_reader = csv.DictReader(io.StringIO(decoded_content))
    
    questions_to_save = []
    row_count = 0
    
    for row in csv_reader:
        row_count += 1
        q_type = row.get("Question_Type", "").strip()
        if not q_type:
            continue # Skip empty rows
            
        diff = row.get("Difficulty", "").strip() or "Medium"
        q_en = row.get("Question_EN", "").strip()
        q_hi = row.get("Question_HI", "").strip() or "[Hindi Missing]"
        ans_en = row.get("Answer_EN", "").strip()
        ans_hi = row.get("Answer_HI", "").strip() or "[Hindi Missing]"
        
        if not q_en or not ans_en:
            continue # Skip invalid rows
            
        options_json = None
        if q_type == "MCQ":
            opts = {}
            for key, col in [("A", "Option_A"), ("B", "Option_B"), ("C", "Option_C"), ("D", "Option_D")]:
                val = row.get(col, "").strip()
                if val:
                    opts[key] = val if "/" in val else f"{val} / [Hindi Missing]"
            if opts:
                options_json = json.dumps(opts)
                
        new_q = models.Question(
            subject_id=subject_id,
            q_type=q_type,
            difficulty=diff,
            question_en=q_en,
            question_hi=q_hi,
            answer_en=ans_en,
            answer_hi=ans_hi,
            options=options_json
        )
        questions_to_save.append(new_q)
        
    if not questions_to_save:
        raise HTTPException(status_code=400, detail="No valid questions found in the CSV. Please check the template formatting.")
        
    db.add_all(questions_to_save)
    db.commit()
    
    return {"message": f"Successfully imported {len(questions_to_save)} questions.", "imported_count": len(questions_to_save)}

@router.post("/papers/generate/")
def generate_paper(request: schemas.PaperGenerationRequest, db: Session = Depends(get_db)):
    subject = db.query(models.Subject).filter(models.Subject.id == request.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Generate Examination Code safely
    month_suffix = datetime.datetime.now().strftime("%b").upper()
    
    # Extract shortcode for Exam Type
    type_map = {"Main": "M", "Back": "B", "Special Back": "SB"}
    type_suffix = type_map.get(request.exam_type, "M")
    
    # Append random integers to prevent breaking uniqueness constraint if users compile multiple exact matches
    rand_id = random.randint(10000, 99999)
    exam_code = f"{subject.subject_code}-{month_suffix}-{type_suffix}-{rand_id}"
    
    # Create the Examination Registry Record
    db_exam = models.Examination(
        branch=subject.branch_name,
        branch_code=subject.branch_code,
        exam_code=exam_code,
        exam_title=request.exam_title,
        subject=subject.name,
        subject_code=subject.subject_code,
        exam_type=request.exam_type
    )
    db.add(db_exam)
        
    sections_json = {}
    section_meta = {}
    calculated_total_marks = 0
    
    # Process each section
    for section in request.sections_config:
        sec_name = section.name
        
        calculated_total_marks += (section.attempt_any * section.marks_per_q)
        
        sec_items = []
        for tc in section.types_config:
            questions = paper_generator.build_paper(db, request.subject_id, tc.num_q, tc.q_type, exam_code=exam_code)
            
            for q in questions:
                merged_q = f"{q.question_en} / {q.question_hi}"
                merged_a = f"{q.answer_en} / {q.answer_hi}"
                
                options = None
                if q.options:
                    try:
                        options = json.loads(q.options)
                    except (json.JSONDecodeError, TypeError):
                        pass
                        
                sec_items.append({"q": merged_q, "options": options, "a": merged_a})
                
        sections_json[sec_name] = sec_items
        section_meta[sec_name] = {
            "attempt_any": section.attempt_any,
            "marks_per_q": section.marks_per_q,
            "total_q": section.total_q
        }
            
    # Format MM as int if no decimals
    if calculated_total_marks == int(calculated_total_marks):
        calculated_total_marks = int(calculated_total_marks)
        
    subject_info = {
        "exam_title": request.exam_title,
        "subject_name": subject.name,
        "subject_code": subject.subject_code,
        "branch_name": subject.branch_name,
        "branch_code": subject.branch_code,
        "sem_year": subject.sem_year,
        "total_marks": calculated_total_marks
    }
    
    paper_path = exporter.export_paper_docx(sections_json, section_meta, subject_info, is_answer_key=False)
    ans_path = exporter.export_paper_docx(sections_json, section_meta, subject_info, is_answer_key=True)
    
    # Save paper record (now storing exam_title context via the document itself)
    paper = models.Paper(
        subject_id=subject.id,
        status="completed",
        file_url_docx=paper_path,
        ans_url_docx=ans_path
    )
    db.add(paper)
    db.commit()
    
    return {"message": "Paper generated successfully", "paper_file": paper_path, "ans_key_file": ans_path}

@router.get("/analytics/subject/{subject_code}", response_model=schemas.SubjectAnalyticsResponse)
def get_subject_analytics(subject_code: str, db: Session = Depends(get_db)):
    from sqlalchemy import func
    
    subject = db.query(models.Subject).filter(models.Subject.subject_code == subject_code).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
        
    # Aggregate total questions and used questions per type
    stats = db.query(
        models.Question.q_type,
        func.count(models.Question.id).label('total'),
        func.sum(
            func.cast(models.Question.usage_count > 0, models.Integer)
        ).label('used')
    ).filter(
        models.Question.subject_id == subject.id
    ).group_by(
        models.Question.q_type
    ).all()
    
    q_types = ["MCQ", "FIB", "T/F", "SA", "LA", "CASE"]
    breakdown = {qt: {"total": 0, "used": 0} for qt in q_types}
    
    total_q = 0
    for q_type, total, used in stats:
        if q_type in breakdown:
            breakdown[q_type] = {"total": total or 0, "used": used or 0}
        total_q += (total or 0)
        
    return {
        "subject_code": subject_code,
        "total_questions": total_q,
        "breakdown": breakdown
    }

@router.post("/examinations/", response_model=schemas.ExaminationResponse)
def create_examination(exam: schemas.ExaminationCreate, db: Session = Depends(get_db)):
    db_exam = models.Examination(**exam.dict())
    db.add(db_exam)
    db.commit()
    db.refresh(db_exam)
    return db_exam

@router.get("/examinations/", response_model=list[schemas.ExaminationResponse])
def get_examinations(db: Session = Depends(get_db)):
    return db.query(models.Examination).all()
