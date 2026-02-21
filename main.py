from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import hashlib
import datetime
import base64
import re
import io
from PIL import Image
import pytesseract

# ---- Permission Detection Engine ----
# Common permissions that apps might request
ALL_PERMISSIONS = {
    "location": ["location", "gps", "geolocation", "your location", "precise location", "approximate location"],
    "camera": ["camera", "take photos", "capture video", "record video"],
    "microphone": ["microphone", "record audio", "voice recording", "audio recording"],
    "contacts": ["contacts", "address book", "phone contacts", "contact list"],
    "storage": ["storage", "files", "photos", "media", "documents", "file access"],
    "phone": ["phone", "call log", "phone calls", "make calls", "phone state"],
    "sms": ["sms", "text messages", "mms", "send sms", "read sms"],
    "calendar": ["calendar", "events", "schedule", "appointments"],
    "biometric": ["fingerprint", "face id", "biometric", "face recognition"],
    "bluetooth": ["bluetooth", "bluetooth devices", "pair devices"],
    "wifi": ["wi-fi", "wifi", "wireless network", "network connections"],
    "notifications": ["notifications", "push notifications", "alerts"],
    "background_data": ["background data", "background refresh", "run in background"],
    "advertising": ["advertising id", "ads", "personalized ads", "tracking"],
    "analytics": ["analytics", "usage data", "crash reports", "telemetry"],
    "social": ["social media", "facebook", "twitter", "instagram", "linkedin"],
    "payment": ["payment", "credit card", "billing", "purchase", "financial"],
    "health": ["health", "fitness", "heart rate", "step count", "medical"],
    "email": ["email", "email address", "mail"],
}

# Essential permissions for different app categories
APP_PERMISSIONS = {
    "ride sharing": ["location", "storage", "notifications", "payment"],
    "ride-sharing": ["location", "storage", "notifications", "payment"],
    "navigation": ["location", "storage", "notifications"],
    "maps": ["location", "storage", "notifications"],
    "social media": ["camera", "storage", "notifications", "contacts"],
    "social": ["camera", "storage", "notifications", "contacts"],
    "messaging": ["camera", "microphone", "storage", "notifications", "contacts"],
    "chat": ["camera", "microphone", "storage", "notifications", "contacts"],
    "video call": ["camera", "microphone", "notifications"],
    "video calling": ["camera", "microphone", "notifications"],
    "photo editing": ["camera", "storage"],
    "photo": ["camera", "storage"],
    "camera": ["camera", "storage"],
    "music": ["storage", "notifications"],
    "music player": ["storage", "notifications"],
    "video player": ["storage", "notifications"],
    "streaming": ["storage", "notifications", "wifi"],
    "fitness": ["location", "storage", "notifications", "health", "biometric"],
    "health": ["health", "storage", "notifications", "biometric"],
    "banking": ["notifications", "biometric", "camera"],
    "finance": ["notifications", "biometric", "camera", "payment"],
    "payment": ["notifications", "biometric", "camera", "payment"],
    "shopping": ["camera", "storage", "notifications", "payment"],
    "e-commerce": ["camera", "storage", "notifications", "payment"],
    "news": ["notifications", "storage"],
    "weather": ["location", "notifications"],
    "calendar": ["calendar", "notifications", "storage"],
    "productivity": ["storage", "notifications", "calendar"],
    "notes": ["storage", "notifications", "camera"],
    "document": ["storage", "notifications", "camera"],
    "file manager": ["storage"],
    "file": ["storage"],
    "game": ["storage", "notifications"],
    "gaming": ["storage", "notifications"],
    "email": ["email", "storage", "notifications", "contacts"],
    "mail": ["email", "storage", "notifications", "contacts"],
    "vpn": ["wifi", "notifications"],
    "browser": ["location", "storage", "notifications"],
    "web browser": ["location", "storage", "notifications"],
}

def detect_permissions(text: str):
    """Detect permissions mentioned in the ToS text"""
    if not text:
        return []
    
    lower_text = text.lower()
    detected = []
    
    for permission, keywords in ALL_PERMISSIONS.items():
        for keyword in keywords:
            if keyword in lower_text:
                detected.append(permission)
                break
    
    return detected

def get_required_permissions(app_purpose: str):
    """Get permissions required for the app purpose"""
    lower_purpose = app_purpose.lower()
    
    for category, permissions in APP_PERMISSIONS.items():
        if category in lower_purpose:
            return permissions
    
    # Default minimal permissions for unknown categories
    return ["storage", "notifications"]

def analyze_permission_risk(app_purpose: str, tos_text: str):
    """Analyze if ToS requests permissions beyond what's needed"""
    required = get_required_permissions(app_purpose)
    requested = detect_permissions(tos_text)
    
    # Find high-risk permissions (requested but not required)
    high_risk = [p for p in requested if p not in required]
    
    # Find legitimately needed permissions
    legitimate = [p for p in requested if p in required]
    
    return {
        "required": required,
        "requested": requested,
        "high_risk": high_risk,
        "legitimate": legitimate
    }

def extract_text_from_images(images: list):
    """Extract text from images using OCR"""
    extracted_text = ""
    
    for img_data in images:
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(img_data.base64)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Extract text using pytesseract
            text = pytesseract.image_to_string(image)
            extracted_text += text + "\n"
        except Exception as e:
            print(f"OCR Error for image: {e}")
            continue
    
    return extracted_text


def generate_email_template(app_purpose: str, high_risk_permissions: list):
    """Generate a professional email template for negotiation"""
    if not high_risk_permissions:
        return f"""Dear [Company Name],

Thank you for providing your Terms of Service for your {app_purpose} application.

After reviewing the document, I am pleased to note that the permissions requested align well with the app's intended purpose. I have no concerns at this time and look forward to using your service.

Best regards,
[Your Name]"""

    permissions_list = ", ".join([p.title() for p in high_risk_permissions])
    
    return f"""Dear [Company Name],

I am writing regarding your Terms of Service for your {app_purpose} application.

After careful review, I have identified certain permission requests that appear to extend beyond what is necessary for the app's core functionality:

**Permissions of Concern:** {permissions_list}

As a user who values privacy and data security, I would appreciate clarification on:
1. Why these additional permissions are required for the app's stated purpose
2. How the data collected through these permissions will be used and stored
3. Whether there is an option to use the app with limited permissions
4. If you offer a version of the app that respects user privacy more stringently

I believe that transparent data practices build stronger customer relationships. I would be happy to continue using your service if these concerns can be addressed satisfactorily.

I look forward to your prompt response within 14 business days.

Sincerely,
[Your Name]
[Your Email]
[Date]"""


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ImageData(BaseModel):
    base64: str
    mime_type: str

class ContractRequest(BaseModel):
    app_purpose: str
    contract_text: str = ""
    images: list[ImageData] = []


@app.get("/")
async def root():
    return FileResponse("index.html")


@app.post("/analyze-contract")
async def analyze_contract(request: ContractRequest):

    if not request.app_purpose:
        raise HTTPException(status_code=400, detail="App purpose required.")

    if not request.contract_text and not request.images:
        raise HTTPException(status_code=400, detail="Provide text or images.")

    timestamp = datetime.datetime.now().isoformat()

    data_hash = request.contract_text + "".join([img.base64 for img in request.images])
    contract_hash = hashlib.sha256(data_hash.encode()).hexdigest()

    # Combine text input with OCR-extracted text from images
    combined_text = request.contract_text
    
    if request.images:
        ocr_text = extract_text_from_images(request.images)
        combined_text += "\n" + ocr_text

    # Analyze permissions
    permission_analysis = analyze_permission_risk(request.app_purpose, combined_text)
    
    # Generate email template
    email_template = generate_email_template(request.app_purpose, permission_analysis["high_risk"])

    return {
        "permissions": {
            "required": permission_analysis["required"],
            "requested": permission_analysis["requested"],
            "high_risk": permission_analysis["high_risk"],
            "legitimate": permission_analysis["legitimate"]
        },
        "email_template": email_template,
        "proof_of_state": {
            "hash": contract_hash,
            "timestamp": timestamp
        }}