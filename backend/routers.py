from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func
from typing import Optional
from .database import get_db, update_engine
from . import schemas, models
from .services import paper_generator, exporter
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
        os.environ["DATABASE_URL"] = db_url
        return {"message": "Database configuration updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        decoded_content = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV file must be UTF-8 encoded.")

    csv_reader = csv.DictReader(io.StringIO(decoded_content))
    
    questions_to_save = []
    # Normalize any variant to canonical types used by the frontend
    IMPORT_TYPE_MAP = {
        "mcq": "MCQ", "multiple choice": "MCQ",
        "t/f": "T/F", "tf": "T/F", "true/false": "T/F", "true false": "T/F",
        "fib": "FIB", "fill in the blanks": "FIB", "fill in the blank": "FIB",
        "sa": "SA", "short answer": "SA",
        "la": "LA", "long answer": "LA",
        "case": "CASE", "case-based": "CASE",
    }
    for row in csv_reader:
        q_type_raw = row.get("Question_Type", "").strip()
        if not q_type_raw:
            continue
        q_type = IMPORT_TYPE_MAP.get(q_type_raw.lower(), q_type_raw)
            
        diff = row.get("Difficulty", "").strip() or "Medium"
        q_en = row.get("Question_EN", "").strip()
        q_hi = row.get("Question_HI", "").strip() or "[Hindi Missing]"
        ans_en = row.get("Answer_EN", "").strip()
        ans_hi = row.get("Answer_HI", "").strip() or "[Hindi Missing]"
        
        if not q_en or not ans_en:
            continue
            
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
        raise HTTPException(status_code=400, detail="No valid questions found in the CSV.")
        
    db.add_all(questions_to_save)
    db.commit()
    
    return {"message": f"Successfully imported {len(questions_to_save)} questions.", "imported_count": len(questions_to_save)}

@router.post("/papers/generate/")
def generate_paper(request: schemas.PaperGenerationRequest, db: Session = Depends(get_db)):
    import traceback
    try:
        subject = db.query(models.Subject).filter(models.Subject.id == request.subject_id).first()
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")

        month_suffix = datetime.datetime.now().strftime("%b").upper()
        type_map = {"Main": "M", "Back": "B", "Special Back": "SB"}
        type_suffix = type_map.get(request.exam_type, "M")
        rand_id = random.randint(10000, 99999)
        exam_code = f"{subject.subject_code}-{month_suffix}-{type_suffix}-{rand_id}"
        
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
        
        sections_data = {}
        section_meta = {}
        total_marks = 0

        for s_config in request.sections_config:
            all_section_qs = []
            # Type alias map: frontend value -> all possible DB values
            TYPE_ALIASES = {
                "T/F": ["T/F", "TF", "True/False", "true/false"],
                "FIB": ["FIB", "Fill in the Blanks", "Fill in the Blank", "fill in the blanks"],
                "SA": ["SA", "Short Answer", "short answer"],
                "LA": ["LA", "Long Answer", "long answer"],
                "MCQ": ["MCQ", "mcq", "Multiple Choice"],
                "CASE": ["CASE", "Case-Based", "case-based"],
            }
            for tc in s_config.types_config:
                query = db.query(models.Question).filter(
                    models.Question.subject_id == request.subject_id
                )
                if tc.q_type != "Mixed":
                    aliases = TYPE_ALIASES.get(tc.q_type, [tc.q_type])
                    query = query.filter(models.Question.q_type.in_(aliases))
                
                questions = query.order_by(models.Question.usage_count.asc(), func.random()).limit(tc.num_q).all()
                for q in questions:
                    q.usage_count += 1
                all_section_qs.extend(questions)
            
            random.shuffle(all_section_qs)
            
            q_dicts = []
            for q in all_section_qs:
                opts = json.loads(q.options) if q.options else None
                q_dicts.append({
                    "q_type": q.q_type,
                    "q": q.question_en,
                    "q_hi": q.question_hi,
                    "a": q.answer_en,
                    "a_hi": q.answer_hi,
                    "options": opts
                })
                
            sections_data[s_config.name] = q_dicts
            section_meta[s_config.name] = {
                "attempt_any": s_config.attempt_any,
                "marks_per_q": s_config.marks_per_q
            }
            num_to_attempt = s_config.attempt_any if s_config.attempt_any else len(q_dicts)
            total_marks += num_to_attempt * s_config.marks_per_q

        db.commit()
        
        subject_info = {
            "exam_type": db_exam.exam_type,
            "branch": db_exam.branch,
            "branch_code": subject.branch_code,
            "sem": subject.sem_year if hasattr(subject, 'sem_year') else "Unknown",
            "exam_title": db_exam.exam_title,
            "subject_code": db_exam.subject_code,
            "subject_name": db_exam.subject,
            "total_marks": total_marks,
            "duration": "3 Hours"
        }
        
        paper_file = exporter.export_paper_docx(sections_data, section_meta, subject_info, is_answer_key=False)
        ans_key_file = exporter.export_paper_docx(sections_data, section_meta, subject_info, is_answer_key=True)
        
        return {
            "exam_code": exam_code,
            "paper_file": paper_file,
            "ans_key_file": ans_key_file
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/subject/{subject_code}")
def get_subject_analytics(subject_code: str, db: Session = Depends(get_db)):
    subject = db.query(models.Subject).filter(models.Subject.subject_code == subject_code).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    questions = db.query(models.Question).filter(models.Question.subject_id == subject.id).all()
    breakdown = {}
    for q in questions:
        qt = q.q_type
        if qt not in breakdown:
            breakdown[qt] = {"total": 0, "used": 0, "fresh": 0, "max_usage": 0}
        breakdown[qt]["total"] += 1
        if q.usage_count > 0:
            breakdown[qt]["used"] += 1
        else:
            breakdown[qt]["fresh"] += 1
        if q.usage_count > breakdown[qt]["max_usage"]:
            breakdown[qt]["max_usage"] = q.usage_count
            
    return {
        "subject_name": subject.name,
        "subject_code": subject.subject_code,
        "total_questions": len(questions),
        "breakdown": breakdown
    }

@router.post("/subjects/{subject_id}/reset-pool/")
def reset_question_pool(subject_id: int, db: Session = Depends(get_db)):
    """Reset usage_count for all questions of a subject so they can be reused."""
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    count = db.query(models.Question).filter(
        models.Question.subject_id == subject_id
    ).update({models.Question.usage_count: 0}, synchronize_session=False)
    db.commit()
    
    return {"message": f"Reset {count} questions for '{subject.name}'. All questions are now fresh."}
