# 🌾 FasalBima Pramaan
Digital Crop Insurance Claim Assistant for PMFBY

FasalBima Pramaan is a web-based platform that simplifies the process of filing crop insurance claims under the Pradhan Mantri Fasal Bima Yojana (PMFBY). Farmers often face language barriers, limited digital literacy, and cumbersome paperwork when reporting crop damage. This platform addresses that gap by allowing farmers to file claims through multilingual voice input or a simple guided form, backed by AI-based crop damage assessment, automated weather validation, and a verifiable PDF evidence report. It is built for farmers, insurance surveyors, and PMFBY administrators who need a faster, more transparent claim-filing and verification process.

## Key Features

- Guided, multi-step claim filing flow (farmer details, crop details, damage details, evidence upload, review)
- Voice-assisted data entry in Kannada and English
- AI-based crop damage classification from uploaded images using EfficientNetB0
- Automatic weather validation against reported damage date and location
- Crop image evidence upload with per-image classification results
- Claim listing, retrieval, and status tracking
- Farmer identity capture with Aadhaar number validation, stored securely and masked wherever displayed
- Auto-generated PDF evidence report with QR code verification
- Responsive web interface

## Technology Stack

**Frontend**
- React
- Vite
- Axios

**Backend**
- FastAPI
- SQLAlchemy
- SQLite

**AI/ML**
- TensorFlow
- EfficientNetB0
- Pillow

**Supporting Libraries**
- ReportLab (PDF generation)
- qrcode (QR code generation)
- Uvicorn (ASGI server)

## Project Structure

```
fasalbima-pramaan/
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy ORM models (Farmer, Claim, Evidence)
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── routers/         # API route definitions
│   │   ├── services/        # Business logic (claims, PDF, weather, classifier)
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/            # NewClaimPage, ViewClaimPage, SuccessPage, LandingPage
│   │   ├── components/       # FormField, Header, EvidenceUploader, etc.
│   │   ├── context/           # LanguageContext
│   │   ├── locales/           # en.js, kn.js
│   │   └── App.jsx
│   └── package.json
│
└── README.md
```

## Installation

### Clone the repository

```bash
git clone https://github.com/<your-username>/fasalbima-pramaan.git
cd fasalbima-pramaan
```

### Backend setup

```bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Frontend setup

```bash
cd frontend

npm install
```

## Running the Application

Start the backend:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

Backend runs at:

```
http://localhost:8000
```

Start the frontend (in a separate terminal):

```bash
cd frontend
npm run dev
```

Frontend runs at:

```
http://localhost:5173
```

## Application Workflow

```
Farmer
  |
  v
Create Claim
  |
  v
Voice Input / Manual Form
  |
  v
Upload Evidence Images
  |
  v
AI Crop Damage Classification
  |
  v
Weather Validation
  |
  v
View Claim
  |
  v
Generate & Download PDF Report
```
