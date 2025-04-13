import fitz
import pytesseract
from pdf2image import convert_from_path
import re
import os
from PIL import Image
import json
from datetime import datetime
from google import genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Google Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def insert_text_to_file(filepath, text_to_insert):
    try:
        with open(filepath, 'w') as file:
            file.write(text_to_insert)
        print(f"Text successfully written to {filepath}")
    except Exception as e:
        print(f"An error occurred: {e}")

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF using a hybrid approach (PyMuPDF + OCR)."""
    doc = fitz.open(pdf_path)
    extracted_text = []

    for page_num, page in enumerate(doc):
        # Try extracting text normally
        text = page.get_text("text")

        if text.strip():  # If text is found, use it
            extracted_text.append(text)
        else:  # If no text found, apply OCR on image
            print(f"Applying OCR on page {page_num + 1} (scanned image detected)...")
            image = convert_from_path(pdf_path, first_page=page_num+1, last_page=page_num+1)[0]
            text = pytesseract.image_to_string(image)
            extracted_text.append(text)

    full_text = "\n".join(extracted_text)
    return full_text

def extract_images_from_pdf(pdf_path, output_folder="extracted_images"):
    """Extracts and saves images from a PDF."""
    doc = fitz.open(pdf_path)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    image_count = 0
    for page_num, page in enumerate(doc):
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]  # Image reference ID
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]  # Image format (e.g., PNG, JPEG)

            image_filename = f"{output_folder}/page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
            with open(image_filename, "wb") as f:
                f.write(image_bytes)

            image_count += 1
            print(f"✅ Saved image: {image_filename}")

    if image_count == 0:
        print("❌ No images found in the PDF.")
    else:
        print(f"✅ Extracted {image_count} images.")

def save_extraction_to_json(text_data, images_folder, output_filepath):
    """Saves extracted text and image references into a structured JSON format."""
    extracted_data = {"document_title": "Extracted Report", "sections": []}

    for page_num, text in enumerate(text_data.split("\n\n")):
        page_info = {
            "page": page_num + 1,
            "text": text.strip(),
            "images": []
        }

        # Find corresponding images for this page
        for img_file in os.listdir(images_folder):
            if f"page_{page_num + 1}_" in img_file:
                page_info["images"].append({
                    "filename": os.path.join(images_folder, img_file),
                    "description": "Extracted image"
                })

        extracted_data["sections"].append(page_info)
    
    final_path = os.path.join(output_filepath, "extracted_data.json")
    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, indent=4)

    print(f"✅ JSON saved as {final_path}")
    return final_path

def run_demo_pdf_data_extraction(pdf_path: str):
    folder_name = os.path.splitext(pdf_path)[0] + datetime.now().strftime("%m%d%Y-%H%M%S%f")
    os.mkdir(folder_name)

    pdf_text = extract_text_from_pdf(pdf_path)
    text_file_path = os.path.join(folder_name, 'result-hybrid-unprocessed.txt')
    insert_text_to_file(text_file_path, pdf_text)
    image_folder_path = os.path.join(folder_name, "extracted_images")
    extract_images_from_pdf(pdf_path, output_folder=image_folder_path)
    extractedDataJsonPath = save_extraction_to_json(pdf_text, image_folder_path, folder_name)
    return {
        "folderName": folder_name,
        "extractedDataJsonPath": extractedDataJsonPath
    }

def extract_and_save_json(text, output_filename="output.json"):
    """Extracts JSON content from a string and saves it as a raw JSON file."""
    match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)

    if match:
        json_content = match.group(1)
        try:
            json_data = json.loads(json_content)
            with open(output_filename, "w", encoding="utf-8") as json_file:
                json.dump(json_data, json_file, indent=4, ensure_ascii=False)
            print(f"JSON data extracted and saved to {output_filename}")
            return json_data
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
    else:
        print("No valid JSON found in the input string.")
    return None

def load_extracted_json(json_path):
    """Loads the extracted JSON file containing structured page-wise data."""
    with open(json_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def query_gemini_for_summary(document_text):
    """Sends the entire document text to Gemini and extracts key insights."""
    prompt = (
        "Analyze the following document text and generate a structured JSON output with:\n"
        "- 'document_overview' (a large paragraph summarizing the document)\n"
        "- 'key_points' (a list of essential takeaways from the document)\n"
        "- 'main_topics' (a list of core topics covered in the document, maximum 4 words per topic)\n\n"
        "Document Text:\n" + document_text
    )

    try:
        response = client.models.generate_content(model="gemma-3-27b-it", contents=prompt)
        return response.text if response else "No response"
    except Exception as e:
        print(f"Error querying Gemini API: {e}")
        return None

def process_pdf_with_gemini_summary(json_path, output_folder):
    data = load_extracted_json(json_path)

    if "sections" not in data:
        print("Invalid JSON structure: 'sections' key missing.")
        return {"error": "Invalid JSON structure: 'sections' key missing."}

    document_text = "\n\n".join(
        section.get("text", "").strip()
        for section in data["sections"]
        if section.get("text")
    )

    if not document_text:
        print("No valid text found in the document.")
        return {"error": "No valid text found in the document."}

    print("Processing entire document with Gemini for structured summary...")
    response_text = query_gemini_for_summary(document_text)

    summary_path = os.path.join(output_folder, "document_summary.json")
    structured_output = extract_and_save_json(response_text, summary_path)

    if structured_output:
        print(summary_path)
        print(f"Document summary successfully saved in {summary_path}")
        return structured_output
    else:
        print("Failed to extract structured JSON from Gemini response.")
        return {"error": "Failed to extract structured JSON from Gemini response."}

def generate_mcqs_chunked(pdf_data, start_page=1, chunk_size=5):
    end_page = start_page + chunk_size - 1

    filtered_sections = [
        section for section in pdf_data.get("sections", [])
        if start_page <= section.get("page", 0) <= end_page
    ]

    if not filtered_sections:
        return {"error": "No pages found in the specified range."}

    combined_text = "\n\n".join(section["text"] for section in filtered_sections)

    prompt = f"""
              You are a helpful AI assistant that creates multiple-choice questions (MCQs) for exam preparation.

              Generate 5 to 7 MCQs as you can based strictly on the following academic text.
              The questions should cover main topics discussed in the text.
              Each question must include:
              - a "question" string,
              - an "options" array of 4 strings,
              - a correct "answer" string (must match one of the options exactly).

              Return the response as a valid JSON list of dictionaries.

              TEXT:
              \"\"\"
              {combined_text}
              \"\"\"
              """

    try:
        response = client.models.generate_content(model="gemma-3-27b-it", contents=prompt)
        raw_output = response.text.strip()

        start_idx = raw_output.find("[")
        end_idx = raw_output.rfind("]") + 1
        json_str = raw_output[start_idx:end_idx]

        mcqs = json.loads(json_str)
        return mcqs

    except Exception as e:
        print("❌ Gemini Error:", e)
        print("📤 Raw Output:\n", raw_output)
        return {"error": "Failed to parse MCQs from Gemini."} 