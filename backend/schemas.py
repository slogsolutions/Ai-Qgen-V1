from pydantic import BaseModel
from typing import Optional, List


class SubjectBase(BaseModel):
    subject_code: str
    name: str
    branch_name: str
    branch_code: str
    sem_year: str
    year: str

class SubjectCreate(SubjectBase):
    pass

class SubjectResponse(SubjectBase):
    id: int
    class Config:
        from_attributes = True

class ExaminationBase(BaseModel):
    branch: str
    branch_code: str
    exam_code: str
    exam_title: str
    subject: str
    subject_code: str

class ExaminationCreate(ExaminationBase):
    pass

class ExaminationResponse(ExaminationBase):
    id: int
    class Config:
        from_attributes = True

class AnalyticsTypeCount(BaseModel):
    total: int
    used: int

class SubjectAnalyticsResponse(BaseModel):
    subject_code: str
    total_questions: int
    breakdown: dict # e.g. {"MCQ": {"total": 10, "used": 5}, ...}


class QuestionBase(BaseModel):
    q_type: str
    difficulty: str = "Medium"
    question_en: str
    question_hi: str
    answer_en: str
    answer_hi: str
    options: Optional[str] = None # JSON string of options

class QuestionCreate(QuestionBase):
    subject_id: int

class QuestionResponse(QuestionBase):
    id: int
    subject_id: int
    usage_count: int
    options: Optional[str] = None
    class Config:
        from_attributes = True

class SectionTypeConstraint(BaseModel):
    q_type: str
    num_q: int

class SectionConfig(BaseModel):
    name: str
    total_q: int
    attempt_any: int
    marks_per_q: float
    types_config: List[SectionTypeConstraint] = []

class PaperGenerationRequest(BaseModel):
    subject_id: int
    exam_title: str
    exam_type: str
    total_marks: int = 100
    sections_config: List[SectionConfig] = []
