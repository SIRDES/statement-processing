from fastapi import FastAPI, File, UploadFile, HTTPException
from concurrent.futures import ProcessPoolExecutor
import pdfplumber
from io import BytesIO
import os
import fitz  # PyMuPDF

app = FastAPI()

def extract_tables_from_page(pdf_path, page_num):
    """Extract tables from a single page using pdfplumber and calculate the score."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_num]
            table = page.extract_tables()
            if table:
                table = table[0]  # Extract the first table found
                column_heads = table[1]
                amount_index = column_heads.index("AMOUNT")
                pageRows = table[2:]
                
                score = sum(float(row[amount_index]) for row in pageRows if row[amount_index])
                
                return {"pageRows": pageRows, "score": score}
            else:
                return []
    except Exception as e:
        return {"error": str(e)}

@app.post("/statement")
async def upload_bank_statement(file: UploadFile = File(...), save_format: str = "csv"):
    if not file:
        raise HTTPException(status_code=400, detail="File is missing. Please upload a PDF file.")
    
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are allowed.")
    
    try:
        # Save the uploaded file to disk for pdfplumber to access
        pdf_path = "/tmp/uploaded_file.pdf"
        with open(pdf_path, "wb") as buffer:
            buffer.write(await file.read())
        
        # Open the PDF using PyMuPDF to get the number of pages quickly
        doc = fitz.open(pdf_path)
        # numOfPages = 2
        numOfPages = doc.page_count

        # Use ProcessPoolExecutor to process pages in parallel
        with ProcessPoolExecutor() as executor:
            results = list(executor.map(extract_tables_from_page, [pdf_path] * numOfPages, range(numOfPages)))


        totalScore = sum(result["score"] for result in results if "score" in result)

        print(f'Processed {len(results)} pages')
        print(f'Total Amount: {totalScore}')

        return {"message": "PDF processed","totalScore": totalScore,"numberOfPages": len(results), "data": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up: remove the saved file
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
