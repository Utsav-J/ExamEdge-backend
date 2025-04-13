# ExamEdge Edging API
This API provides endpoints for processing PDF files, generating summaries, and creating multiple-choice questions (MCQs) using Google's Gemini AI.

## Setup

1. Install the required dependencies:
```bash
pip install --upgrade --force-reinstall --no-deps -r requirements.txt
```

2. Create a `.env` file in the root directory and add your Gemini API key:
```
GEMINI_API_KEY=your_api_key_here
```

3. Run the FastAPI server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Upload PDF
- **Endpoint**: `POST /upload-pdf/`
- **Description**: Upload a PDF file for processing
- **Request**: Form data with PDF file
- **Response**: JSON with filename and success message

### 2. Generate Summary
- **Endpoint**: `POST /generate-summary/{filename}`
- **Description**: Generate a summary from an uploaded PDF
- **Parameters**: 
  - `filename`: Name of the uploaded PDF file
- **Response**: JSON containing document overview, key points, and main topics

### 3. Generate MCQs
- **Endpoint**: `POST /generate-mcqs/{filename}`
- **Description**: Generate multiple-choice questions from an uploaded PDF
- **Parameters**: 
  - `filename`: Name of the uploaded PDF file
  - `start_page` (optional): Starting page number (default: 1)
- **Response**: JSON containing a list of MCQs

## Example Usage

1. Upload a PDF:
```bash
curl -X POST -F "file=@your_file.pdf" http://localhost:8000/upload-pdf/
```

2. Generate Summary:
```bash
curl -X POST http://localhost:8000/generate-summary/your_file.pdf
```

3. Generate MCQs:
```bash
curl -X POST http://localhost:8000/generate-mcqs/your_file.pdf?start_page=1
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc` 
