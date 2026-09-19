import cv2
import numpy as np
import easyocr
import logging
import io
import pypdfium2 as pdfium

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OCR_Engine")

logger.info("Initializing EasyOCR Model (English + Hindi)...")
reader = easyocr.Reader(['en', 'hi'], gpu=False)

def preprocess_cv_image(img: np.ndarray) -> np.ndarray:
    """Applies grayscale and adaptive thresholding to enhance faded ink and handwritten text."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    processed = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    return processed

def extract_raw_text_from_document(file_bytes: bytes, filename: str) -> str:
    """
    Extracts text from both image formats (JPG/PNG) and multi-page PDF documents.
    """
    extracted_text_chunks = []
    
    # Path 1: Multi-Page PDF Processing
    if filename.lower().endswith('.pdf'):
        logger.info("Rendering PDF pages for OCR extraction...")
        pdf = pdfium.PdfDocument(io.BytesIO(file_bytes))
        for page_idx in range(len(pdf)):
            page = pdf[page_idx]
            pil_image = page.render(scale=2.0).to_pil() # 2x scale for sharper OCR
            cv_img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            cleaned = preprocess_cv_image(cv_img)
            
            page_text = reader.readtext(cleaned, detail=0)
            extracted_text_chunks.extend(page_text)
            
    # Path 2: Direct Image Processing (PNG/JPG)
    else:
        logger.info("Processing single image file...")
        nparr = np.frombuffer(file_bytes, np.uint8)
        cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        cleaned = preprocess_cv_image(cv_img)
        extracted_text_chunks = reader.readtext(cleaned, detail=0)
        
    raw_text = " ".join(extracted_text_chunks)
    logger.info(f"Total extracted text length: {len(raw_text)} characters.")
    return raw_text