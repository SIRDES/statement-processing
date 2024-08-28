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
            fetched_table = page.extract_tables()
            # table = page.extract_tables()
            # table=[]
            if fetched_table:
                # table = table[0]
                if len(fetched_table) == 2:
                    # Merge the two tables
                    table=fetched_table[0] + fetched_table[1]
                    # print(page_num,table)
                else :
                    table = fetched_table[0]
                  # Extract the first table found
                
                # Dynamically find the header and data start
                data_start_index = None
                for i, row in enumerate(table):
                    if all(cell is not None for cell in row):  # Identify a complete header row
                        data_start_index = i + 1
                        column_heads = row
                        break

                if data_start_index is None:
                    return {"error": "No valid table header found"}

                pageRows = table[data_start_index:]  # Get rows after header
                
                amount_index = column_heads.index("AMOUNT")
                transaction_type_index = column_heads.index("TRANS. TYPE")

                # Filter and process data rows only
                pageRows = [row for row in pageRows if row and all(cell is not None for cell in row)]
                
                cash_in = [float(row[amount_index]) for row in pageRows if row[transaction_type_index] == "CASH_IN"]
                cash_out = [float(row[amount_index]) for row in pageRows if row[transaction_type_index] == "CASH_OUT"]

                score = sum(float(row[amount_index]) for row in pageRows if row[amount_index])

                return {"columnHeads": column_heads, "pageRows": pageRows, "score": score, "cash_in": cash_in, "cash_out": cash_out}
            else:
                return {"error": "No table found on this page"}
    except Exception as e:
        # print(e, page_num, table)
        return {"error": str(e)}

@app.post("/api/processScore")
async def upload_bank_statement(statement: UploadFile = File(...), save_format: str = "csv"):
    if not statement:
        raise HTTPException(status_code=400, detail="File is missing. Please upload a PDF file.")
    
    if statement.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are allowed.")
    
    try:
        # Save the uploaded file to disk for pdfplumber to access
        pdf_path = "/tmp/uploaded_statement.pdf"
        with open(pdf_path, "wb") as buffer:
            buffer.write(await statement.read())
        
        # Open the PDF using PyMuPDF to get the number of pages quickly
        doc = fitz.open(pdf_path)
        numOfPages = doc.page_count
        # numOfPages =2
        # Use ProcessPoolExecutor to process pages in parallel
        with ProcessPoolExecutor() as executor:
            results = list(executor.map(extract_tables_from_page, [pdf_path] * numOfPages, range(numOfPages)))

        totalScore = sum(result["score"] for result in results if "score" in result)

        all_cash_in = []
        all_cash_out = []
        for row in results:
            if "cash_in" in row and row["cash_in"]:
                all_cash_in.extend(row["cash_in"])
            if "cash_out" in row and row["cash_out"]:
                all_cash_out.extend(row["cash_out"])

        mean_cash_in = sum(float(row) for row in all_cash_in) / len(all_cash_in) if all_cash_in else 0
        mean_cash_out = sum(float(row) for row in all_cash_out) / len(all_cash_out) if all_cash_out else 0
        
        modal_cash_in = max(set(all_cash_in), key=all_cash_in.count) if all_cash_in else 0
        modal_cash_out = max(set(all_cash_out), key=all_cash_out.count) if all_cash_out else 0
        max_cash_in = max(all_cash_in) if all_cash_in else 0
        max_cash_out = max(all_cash_out) if all_cash_out else 0
        min_cash_in = min(all_cash_in) if all_cash_in else 0
        min_cash_out = min(all_cash_out) if all_cash_out else 0

        # print(f'Processed {len(results)} pages')
        print(f'Total Amount: {totalScore}')

        return {"message": "Statement processed successfully", 
                "data": {"mean_cash_in": mean_cash_in, "mean_cash_out": mean_cash_out, 
                         "modal_cash_in": modal_cash_in, "modal_cash_out": modal_cash_out, 
                         "max_cash_in": max_cash_in, "max_cash_out": max_cash_out, 
                         "min_cash_in": min_cash_in, "min_cash_out": min_cash_out,"all_cash_in": all_cash_in, "all_cash_out": all_cash_out, "total": totalScore}}

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up: remove the saved file
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
