import fitz  # PyMuPDF
from fastapi import UploadFile

def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200) -> list[str]:
    """Splits text into chunks of `chunk_size` characters with `overlap`."""
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def is_junk_block(text: str) -> bool:
    """Identifies if a text block is likely ASCII art, a diagram label, or gibberish."""
    text = text.strip()
    if len(text) < 15:
        return True # Ignore stray labels like "10 MHz" or "100K"
        
    alnum_count = sum(c.isalnum() for c in text)
    if len(text) > 0 and (alnum_count / len(text)) < 0.5:
        return True # Ignore ASCII art / grids (less than 50% alphanumeric)
        
    return False

async def extract_and_chunk_pdf(upload_file: UploadFile, chunk_size: int = 1500, overlap: int = 200) -> list[str]:
    """Extracts text content from a PDF UploadFile and returns it as overlapping chunks."""
    try:
        content = await upload_file.read()
        pdf_document = fitz.open(stream=content, filetype="pdf")
        
        chunks = []
        current_text = ""
        
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            
            # Smart Block Filtering
            blocks = page.get_text("blocks")
            clean_page_text = ""
            
            for b in blocks:
                # b is a tuple: (x0, y0, x1, y1, "text", block_no, block_type)
                if len(b) >= 7 and b[6] == 0: # 0 means Text, 1 means Image
                    block_text = b[4]
                    if not is_junk_block(block_text):
                        clean_page_text += block_text + "\n"
                        
            current_text += clean_page_text + "\n"
            
            # Whenever we accumulate enough text, chunk it to avoid huge memory strings
            if len(current_text) > chunk_size * 5:
                page_chunks = chunk_text(current_text, chunk_size, overlap)
                # Keep the last chunk as overlap for the next page
                if page_chunks:
                    current_text = page_chunks.pop()
                    chunks.extend(page_chunks)
                else:
                    current_text = ""
                    
        # Process remaining text
        if current_text.strip():
            chunks.extend(chunk_text(current_text, chunk_size, overlap))
            
        pdf_document.close()
        return [c for c in chunks if c.strip()]
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")
