import os
import torch
from PIL import Image
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

# Verify GPU availability
if not torch.cuda.is_available():
    raise SystemError("CUDA GPU not detected. Ensure torch with CUDA is installed.")

print(f"--> Initializing on: {torch.cuda.get_device_name(0)}")
print(f"--> Initial VRAM Allocated: {torch.cuda.memory_allocated(0) / (1024**2):.2f} MB")

# Hugging Face model repository
model_id = "Qwen/Qwen2-VL-2B-Instruct"

print("--> Loading Qwen2-VL-2B weights into GPU memory...")
processor = AutoProcessor.from_pretrained(model_id)
model = Qwen2VLForConditionalGeneration.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    device_map="cuda"
)

print(f"--> Model Loaded. VRAM Allocated: {torch.cuda.memory_allocated(0) / (1024**2):.2f} MB")

# Target image path
image_path = "Screenshot 2026-09-17 204840.png"

if not os.path.exists(image_path):
    raise FileNotFoundError(f"Image not found at: {image_path}")

print(f"--> Running inference on: {image_path}")

messages = [
    {
        "role": "user",
        "content": [
            {"type": "image", "image": image_path},
            {
                "type": "text",
                "text": (
                    "Analyze this official Indian public works document image with high precision. "
                    "Extract the following details in strict JSON format: \n"
                    "{\n"
                    '  "document_type": "Exact title/classification of the document",\n'
                    '  "name_of_work": "Full description of the work",\n'
                    '  "sanction_number_and_date": "Sanction order number and date",\n'
                    '  "amount_of_estimate": "Estimated amount numerical value",\n'
                    '  "expenditure": "Actual expenditure numerical value",\n'
                    '  "date_of_commencement": "Commencement date",\n'
                    '  "date_of_completion": "Completion date",\n'
                    '  "has_official_stamp": true or false,\n'
                    '  "has_signature": true or false\n'
                    "}"
                ),
            },
        ],
    }
]

text_prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
image_inputs, video_inputs = process_vision_info(messages)

inputs = processor(
    text=[text_prompt],
    images=image_inputs,
    videos=video_inputs,
    padding=True,
    return_tensors="pt"
).to("cuda")

print("--> Generating forensic extraction on RTX 4060...")
with torch.no_grad():
    generated_ids = model.generate(**inputs, max_new_tokens=512)

generated_ids_trimmed = [
    out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
]
output_text = processor.batch_decode(
    generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
)[0]

print("\n========== LOCAL VLM EXTRACTION OUTPUT ==========")
print(output_text)
print("=================================================")
print(f"--> Final Peak VRAM Used: {torch.cuda.max_memory_allocated(0) / (1024**2):.2f} MB")