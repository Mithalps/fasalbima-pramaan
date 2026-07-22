# 🌾 FasalBima Pramaan

**AI-Powered Crop Insurance Claim Assistant for PMFBY**

FasalBima Pramaan is a Digital platform that simplifies crop insurance claim filing under the Pradhan Mantri Fasal Bima Yojana (PMFBY). The system enables farmers to submit structured claims using multilingual voice input, AI-based crop damage assessment, weather validation, and automated evidence report generation.

---

## Features

- Voice-assisted claim filing (Kannada & English)
- AI crop damage classification using EfficientNetB0
- Automatic weather validation
- Crop image evidence upload
- Claim management and tracking
- Professional PDF evidence report generation
- QR code verification
- Responsive web application

---

## Tech Stack

### Frontend
- React
- Vite
- Axios

### Backend
- FastAPI
- SQLAlchemy
- SQLite

### AI / ML
- TensorFlow
- EfficientNetB0
- Pillow

### Other
- ReportLab
- QRCode
- Uvicorn

---

## Project Workflow

```text
Farmer
   │
   ▼
Create Claim
   │
   ▼
Voice Input / Manual Form
   │
   ▼
Upload Evidence Images
   │
   ▼
AI Crop Damage Classification
   │
   ▼
Weather Validation
   │
   ▼
View Claim
   │
   ▼
Generate & Download PDF Report
```

## Installation

### Clone the repository

```bash
git clone https://github.com/<your-username>/fasalbima-pramaan.git
cd fasalbima-pramaan
```

### Backend

```bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate

pip install -r requirements.txt

python -m uvicorn app.main:app --reload
```

Backend runs at:

```
http://localhost:8000
```

### Frontend

```bash
cd frontend

npm install

npm run dev
```

Frontend runs at:

```
http://localhost:5173
```
