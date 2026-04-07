from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from sqlalchemy.orm import Session
from typing import Optional
from .database import get_db, update_engine
from . import schemas, models
from .services import pdf_extractor, llm_service, paper_generator, exporter, model_fetcher
import json
import os
import re

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
    return model_fetcher.get_groq_models()

@router.post("/generate/from-pdf/")
async def generate_from_pdf(
    subject_id: int, 
    file: UploadFile = File(...), 
    q_types_config: str = Form("[]"),
    difficulty: str = Form("Medium"),
    provider: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    text = await pdf_extractor.extract_text_from_pdf(file)
    
    try:
        types_config = json.loads(q_types_config)
    except Exception:
        types_config = []

    type_limits = {}
    for tc in types_config:
        qt = tc.get("q_type", "Mixed")
        nq = int(tc.get("num_q", 0))
        if nq > 0:
            type_limits[qt] = type_limits.get(qt, 0) + nq

    # Normally this would be a background task (using models.Job)
    try:
        # If ollama selected, ensure it's serving
        if provider == "ollama":
            model_fetcher.ensure_ollama_running()
            
        generated = llm_service.generate_questions(
            subject_context=text, 
            types_config=types_config,
            difficulty=difficulty,
            provider=provider,
            model=model_name
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    saved_qs = []
    type_counts = {}
    
    for q_data in generated:
        if not isinstance(q_data, dict):
            continue
            
        # Extract q_type and options from model response if available
        # Default to "Mixed" if model didn't return one
        actual_q_type = q_data.get("q_type", "Mixed")
        
        # Trim hallucinated extras strictly
        if type_limits:
            current_count = type_counts.get(actual_q_type, 0)
            limit = type_limits.get(actual_q_type, 0)
            
            # Skip if type was never requested or we already reached the limit
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

@router.post("/papers/generate/")
def generate_paper(request: schemas.PaperGenerationRequest, db: Session = Depends(get_db)):
    subject = db.query(models.Subject).filter(models.Subject.id == request.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
        
    sections_json = {}
    section_meta = {}
    calculated_total_marks = 0
    
    # Process each section
    for section in request.sections_config:
        sec_name = section.name
        
        calculated_total_marks += (section.attempt_any * section.marks_per_q)
        
        sec_items = []
        for tc in section.types_config:
            questions = paper_generator.build_paper(db, request.subject_id, tc.num_q, tc.q_type)
            
            for q in questions:
                merged_q = f"{q.question_en} / {q.question_hi}"
                merged_a = f"{q.answer_en} / {q.answer_hi}"
                
                options = None
                if q.options:
                    try:
                        options = json.loads(q.options)
                    except:
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
        "exam_title": subject.exam_title,
        "subject_name": subject.name,
        "subject_code": subject.code,
        "branch_name": subject.branch_name,
        "branch_code": subject.branch_code,
        "sem_year": subject.sem_year,
        "total_marks": calculated_total_marks
    }
    
    paper_path = exporter.export_paper_docx(sections_json, section_meta, subject_info, is_answer_key=False)
    ans_path = exporter.export_paper_docx(sections_json, section_meta, subject_info, is_answer_key=True)
    
    # Save paper record
    paper = models.Paper(
        subject_id=subject.id,
        status="completed",
        file_url_docx=paper_path,
        ans_url_docx=ans_path
    )
    db.add(paper)
    db.commit()
    
    return {"message": "Paper generated successfully", "paper_file": paper_path, "ans_key_file": ans_path}
