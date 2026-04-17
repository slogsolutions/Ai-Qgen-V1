from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    subject_code = Column(String, unique=True, index=True)
    name = Column(String)
    branch_name = Column(String)
    branch_code = Column(String)
    sem_year = Column(String)
    year = Column(String)
    
    questions = relationship("Question", back_populates="subject", cascade="all, delete-orphan")
    papers = relationship("Paper", back_populates="subject", cascade="all, delete-orphan")

class Examination(Base):
    __tablename__ = "examinations"
    id = Column(Integer, primary_key=True, index=True)
    branch = Column(String)
    branch_code = Column(String)
    exam_code = Column(String, unique=True, index=True)
    exam_title = Column(String)
    subject = Column(String)
    subject_code = Column(String)
    exam_type = Column(String)

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"))
    q_type = Column(String) # MCQ, FIB, SA, LA, CASE
    difficulty = Column(String, default="Medium") # Easy, Medium, Hard
    question_en = Column(Text)
    question_hi = Column(Text)
    answer_en = Column(Text)
    answer_hi = Column(Text)
    options = Column(Text, nullable=True) # JSON stored options
    usage_count = Column(Integer, default=0)
    exam_code = Column(String, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subject = relationship("Subject", back_populates="questions")

class Paper(Base):
    __tablename__ = "papers"
    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"))
    status = Column(String) # generating, completed, failed
    file_url_docx = Column(String, nullable=True)
    file_url_pdf = Column(String, nullable=True)
    ans_url_docx = Column(String, nullable=True)
    ans_url_pdf = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subject = relationship("Subject", back_populates="papers")

