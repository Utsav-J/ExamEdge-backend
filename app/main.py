from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from typing import Optional
import json
from .pdf_processor import run_demo_pdf_data_extraction, process_pdf_with_gemini_summary, generate_mcqs_chunked
import uuid

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
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Generate a unique suffix
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]  # Short UUID
    base_name = os.path.splitext(file.filename)[0]
    new_filename = f"{base_name}_{unique_id}.pdf"
    file_path = os.path.join(UPLOAD_DIR, new_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Run extraction once
        extraction_results = run_demo_pdf_data_extraction(file_path)
        metadata_path = os.path.join(UPLOAD_DIR, f"{new_filename}_metadata.json")
        with open(metadata_path, "w") as meta_file:
            json.dump(extraction_results, meta_file)
        return {
            "original_filename": file.filename,
            "unique_filename": new_filename,
            "message": "File uploaded and processed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/generate-summary/{filename}")
async def generate_summary(filename: str):
    """
    Generate a summary from an uploaded PDF file.
    """
    metadata_path = os.path.join(UPLOAD_DIR, f"{filename}_metadata.json")
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Metadata not found. Please upload the PDF first.")

    try:
        with open(metadata_path) as f:
            extraction_results = json.load(f)

        extracted_json_path = extraction_results["extractedDataJsonPath"]
        output_folder = extraction_results["folderName"]

        summary = process_pdf_with_gemini_summary(extracted_json_path, output_folder)

        # Optional: Don't delete the folder if you still need it for MCQs
        # shutil.rmtree(output_folder)

        return summary

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-mcqs/{filename}")
async def generate_mcqs(filename: str, start_page: Optional[int] = 1):
    """
    Generate MCQs from an uploaded PDF file.
    """
    metadata_path = os.path.join(UPLOAD_DIR, f"{filename}_metadata.json")
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Metadata not found. Please upload the PDF first.")

    try:
        with open(metadata_path) as f:
            extraction_results = json.load(f)

        extracted_json_path = extraction_results["extractedDataJsonPath"]

        with open(extracted_json_path) as f:
            data = json.load(f)

        mcqs = generate_mcqs_chunked(data, start_page=start_page)

        # Optional: Clean up here if you're done with both summary and MCQs
        # shutil.rmtree(extraction_results["folderName"])

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
