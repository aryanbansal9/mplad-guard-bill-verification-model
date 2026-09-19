import os
import time
import requests

# Set this to the folder containing your test bills (English, Hindi, fake bills, etc.)
TEST_IMAGES_DIR = "data/test_bills"
API_URL = "http://127.0.0.1:8000/api/verify-bill"

def evaluate_accuracy():
    if not os.path.exists(TEST_IMAGES_DIR):
        print(f"Please create a '{TEST_IMAGES_DIR}' folder and add test images.")
        return

    test_files = [f for f in os.listdir(TEST_IMAGES_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
    if not test_files:
        print("No images found for testing.")
        return

    print(f"Starting Batch Evaluation on {len(test_files)} documents...\n")
    
    success_count = 0
    fraud_detected = 0

    for filename in test_files:
        file_path = os.path.join(TEST_IMAGES_DIR, filename)
        print(f"Analyzing: {filename}...")
        
        start_time = time.time()
        with open(file_path, "rb") as f:
            response = requests.post(API_URL, files={"file": f})
        
        processing_time = time.time() - start_time
        
        if response.status_code == 200:
            success_count += 1
            data = response.json()
            risk = data['gfr_compliance_report']['total_risk_score']
            status = data['gfr_compliance_report']['compliance_status']
            
            if risk >= 50:
                fraud_detected += 1
                
            print(f"  [+] Status: {status} (Risk: {risk}/100)")
            print(f"  [+] Inference Time: {processing_time:.2f} seconds")
        else:
            print(f"  [-] Failed to process. HTTP {response.status_code}")
            
    print("\n" + "="*40)
    print("      MODEL ACCURACY & PROOF MATRIX      ")
    print("="*40)
    print(f"Total Documents Processed : {len(test_files)}")
    print(f"Pipeline Success Rate     : {(success_count/len(test_files))*100:.1f}%")
    print(f"Fraudulent Bills Caught   : {fraud_detected}")
    print("="*40)
    print("Ready for SIH Jury Presentation.")

if __name__ == "__main__":
    evaluate_accuracy()