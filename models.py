from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from database import Base

# Association table for the many-to-many relationship between Resume and Skill
resume_skill_association = Table('resume_skill_association', Base.metadata,
    Column('resume_id', Integer, ForeignKey('resumes.id')),
    Column('skill_id', Integer, ForeignKey('skills.id'))
)

class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True, index=True)
    summary = Column(Text, nullable=True)
    
    personal_info = relationship("PersonalInfo", back_populates="resume", uselist=False, cascade="all, delete-orphan")
    skills = relationship("Skill", secondary=resume_skill_association, back_populates="resumes")
    work_experiences = relationship("WorkExperience", back_populates="resume", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="resume", cascade="all, delete-orphan")
    educations = relationship("Education", back_populates="resume", cascade="all, delete-orphan")

class PersonalInfo(Base):
    __tablename__ = "personal_info"
    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    name = Column(String, index=True)
    
    # --- MODIFIED LINES ---
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, unique=True, index=True, nullable=True)
    # --- END MODIFIED LINES ---
    
    location = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    resume = relationship("Resume", back_populates="personal_info")

class Skill(Base):
    __tablename__ = "skills"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    resumes = relationship("Resume", secondary=resume_skill_association, back_populates="skills")

class WorkExperience(Base):
    __tablename__ = "work_experience"
    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    company = Column(String)
    job_title = Column(String)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    resume = relationship("Resume", back_populates="work_experiences")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    name = Column(String)
    description = Column(Text, nullable=True)
    # Technologies are stored as a comma-separated string for simplicity
    technologies = Column(String, nullable=True)
    resume = relationship("Resume", back_populates="projects")

class Education(Base):
    __tablename__ = "education"
    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    institution = Column(String)
    degree = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    resume = relationship("Resume", back_populates="educations")