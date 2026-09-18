import cv2
import numpy as np
import easyocr
import logging

# Set up logging for hackathon debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OCR_Engine")

# Initialize the EasyOCR reader globally so it doesn't reload on every API call.
# Including 'hi' (Hindi) alongside 'en' is a huge plus for Indian government hackathons!
logger.info("Initializing EasyOCR Model (English + Hindi)...")
reader = easyocr.Reader(['en', 'hi'], gpu=False) # Set gpu=True if you have a dedicated GPU

def preprocess_image_for_ocr(image_bytes: bytes) -> np.ndarray:
    """
    Cleans the uploaded bill image using OpenCV.
    Applies grayscale and adaptive thresholding to remove shadows and enhance handwritten ink.
    """
    # Convert raw bytes to a numpy array, then to an OpenCV image
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 1. Convert to Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Apply Adaptive Thresholding (Great for uneven lighting on paper)
    # Block size 11, C=2 are standard good values for document scanning
    processed_img = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    return processed_img

def extract_raw_text_from_image(image_bytes: bytes) -> str:
    """
    Preprocesses the image and runs EasyOCR to extract all text.
    Returns a single concatenated string of all detected text.
    """
    try:
        # Preprocess the image
        cleaned_image = preprocess_image_for_ocr(image_bytes)
        
        # Run EasyOCR
        # detail=0 returns just the text, not the bounding box coordinates
        result_list = reader.readtext(cleaned_image, detail=0)
        
        # Join the list of strings into one large text block
        raw_text = " ".join(result_list)
        logger.info(f"Successfully extracted {len(raw_text)} characters.")
        
        return raw_text
    
    except Exception as e:
        logger.error(f"OCR Pipeline failed: {str(e)}")
        raise e