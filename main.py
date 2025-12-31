import os
import json
import fitz  
import docx
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
import io
from dotenv import load_dotenv
from typing import List
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import crud, models, schemas
from fastapi.middleware.cors import CORSMiddleware

models.Base.metadata.create_all(bind=engine)

load_dotenv()
try:
    API_KEY = os.environ["GEMINI_API_KEY"]
except KeyError:
    API_KEY = "YOUR_GEMINI_API_KEY"

if API_KEY == "YOUR_GEMINI_API_KEY":
    print("Warning: GEMINI_API_KEY is not set. Please replace 'YOUR_GEMINI_API_KEY' or set the environment variable.")
genai.configure(api_key=API_KEY)

app = FastAPI(
    title="Resume Parser API",
    description="An API that parses resumes (PDF, DOCX) using Gemini and returns structured JSON data.",
    version="1.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            text = "".join(page.get_text() for page in doc)
        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF file: {e}")

def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing DOCX file: {e}")

async def parse_resume_with_gemini(resume_text: str) -> schemas.ResumeData:
    prompt = f"""
    You are an expert resume parsing AI. Your task is to extract key information from the following resume text and provide the output in a clean, structured JSON format.
    The JSON output must strictly adhere to the following schema.
    JSON Schema:
    {json.dumps(schemas.ResumeData.model_json_schema(), indent=2)}
    
    Resume Text:
    {resume_text}
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        # Use await correctly
        response = await model.generate_content_async(prompt)
        
        # DEBUG: Print the response to terminal to see what Gemini said
        print("DEBUG Gemini Response:", response.text)

        # Clean the response
        text_content = response.text
        if "```json" in text_content:
            text_content = text_content.split("```json")[1].split("```")[0]
        
        parsed_json = json.loads(text_content.strip())
        return schemas.ResumeData(**parsed_json)

    except Exception as e:
        # THIS LINE IS CRITICAL: It will print the exact error in your VS Code terminal
        print(f"CRITICAL ERROR IN PARSING: {str(e)}")
        import traceback
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/parse-resume/", response_model=schemas.ResumeData, tags=["Resume Parsing"])
async def parse_and_save_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a resume file (PDF or DOCX), parse it, save the result to the database,
    and return the structured content.
    """
    if not file.content_type in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a PDF or DOCX file.")
    
    file_bytes = await file.read()
    raw_text = ""
    
    if file.content_type == "application/pdf":
        raw_text = extract_text_from_pdf(file_bytes)
    else:
        raw_text = extract_text_from_docx(file_bytes)
    
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from the document.")
    
    structured_data = await parse_resume_with_gemini(raw_text)
    crud.create_or_update_resume(db=db, resume_data=structured_data)
    return structured_data

@app.get("/resumes/{resume_id}", response_model=schemas.ResumeData, tags=["Database"])
def read_resume(resume_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a parsed resume from the database by its ID.
    """
    db_resume = db.query(models.Resume).filter(models.Resume.id == resume_id).first()
    if db_resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    return schemas.ResumeData(
        personal_info=db_resume.personal_info,
        summary=db_resume.summary,
        skills=db_resume.skills,
        work_experience=db_resume.work_experiences,
        projects=db_resume.projects,
        education=db_resume.educations
    )

@app.get("/resumes/search/", response_model=schemas.ResumeData, tags=["Database"])
def search_resume_by_email(email: str, db: Session = Depends(get_db)):
    """
    Retrieve a parsed resume from the database by the candidate's email address.
    """
    personal_info = db.query(models.PersonalInfo).filter(models.PersonalInfo.email == email).first()
    if personal_info is None or personal_info.resume is None:
        raise HTTPException(status_code=404, detail="Resume not found for the provided email")
    
    # Convert SQLAlchemy model to Pydantic schema
    return schemas.ResumeData(
        personal_info=personal_info,
        summary=personal_info.resume.summary,
        skills=personal_info.resume.skills,
        work_experience=personal_info.resume.work_experiences,
        projects=personal_info.resume.projects,
        education=personal_info.resume.educations
    )

@app.get("/resumes/", response_model=List[schemas.ResumeData], tags=["Database"])
def list_all_resumes(db: Session = Depends(get_db)):
    resumes = db.query(models.Resume).all()
    result = []
    for db_resume in resumes:
        resume_data = schemas.ResumeData(
            id=db_resume.id,  # Add this line
            personal_info=db_resume.personal_info,
            summary=db_resume.summary,
            skills=db_resume.skills,
            work_experience=db_resume.work_experiences,
            projects=db_resume.projects,
            education=db_resume.educations
        )
        result.append(resume_data)
    return result
        

@app.delete("/resumes/{resume_id}", tags=["Database"])
def delete_resume(resume_id: int, db: Session = Depends(get_db)):
    """
    Delete a resume from the database by its ID.
    """
    db_resume = db.query(models.Resume).filter(models.Resume.id == resume_id).first()
    if db_resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    db.delete(db_resume)
    db.commit()
    return {"message": f"Resume with ID {resume_id} has been deleted successfully"}

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Resume Parser API. Go to /docs for the API documentation."}