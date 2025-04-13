from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from typing import Optional
import json
from .pdf_processor import run_demo_pdf_data_extraction, process_pdf_with_gemini_summary, generate_mcqs_chunked

app = FastAPI(title="PDF Processing API",
             description="API for processing PDFs and generating summaries and MCQs",
             version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file for processing.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"filename": file.filename, "message": "File uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-summary/{filename}")
async def generate_summary(filename: str):
    """
    Generate a summary from an uploaded PDF file.
    """
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        extraction_results = run_demo_pdf_data_extraction(file_path)
        extracted_json_path = extraction_results["extractedDataJsonPath"]
        output_folder = extraction_results["folderName"]
        
        summary = process_pdf_with_gemini_summary(extracted_json_path, output_folder)
        
        # Clean up the temporary files
        shutil.rmtree(output_folder)
        
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-mcqs/{filename}")
async def generate_mcqs(filename: str, start_page: Optional[int] = 1):
    """
    Generate MCQs from an uploaded PDF file.
    """
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        extraction_results = run_demo_pdf_data_extraction(file_path)
        extracted_json_path = extraction_results["extractedDataJsonPath"]
        
        with open(extracted_json_path) as f:
            data = json.load(f)
        
        mcqs = generate_mcqs_chunked(data, start_page=start_page)
        
        # Clean up the temporary files
        shutil.rmtree(extraction_results["folderName"])
        
        return {"mcqs": mcqs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """
    Root endpoint returning API information.
    """
    return {
        "message": "PDF Processing API",
        "endpoints": {
            "/upload-pdf/": "Upload a PDF file",
            "/generate-summary/{filename}": "Generate summary from uploaded PDF",
            "/generate-mcqs/{filename}": "Generate MCQs from uploaded PDF"
        }
    } 