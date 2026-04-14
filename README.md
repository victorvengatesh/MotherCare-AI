# MotherCare AI

MotherCare AI is a professional healthcare support system designed to provide preliminary guidance through symptom analysis and advanced image classification. It features a **multilingual Voice AI** architecture, support for **Tamil and English**, and an integrated patient history system.

> [!IMPORTANT]
> **SAFETY DISCLAIMER**: MotherCare AI is **NOT** a medical diagnosis tool. All guidance provided is preliminary and intended for informational purposes only. This system is not a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare professional for medical concerns. In case of an emergency, contact your local emergency services immediately.

---

## 🚀 Features

- **Multilingual Voice AI**: Full support for English and Tamil voice input (STT) and output (TTS) using the Web Speech API.
- **ML Image Classification**: Integrated ResNet18 model trained on clinical categories (Skin Allergy, Burn, Wound, Other).
- **Intelligent Symptom Analysis**: Keyword-based symptom recognition with automatic urgency escalation.
- **Patient History Tracking**: Integrated JSON-based history system that identifies recurring symptoms across sessions.
- **Polished UX**: Modern, healthcare-themed responsive dashboard with distinct visual indicators and interactive Voice AI controls.

## 🛠️ Tech Stack

- **Frontend**: React (Vite) with Vanilla CSS and Web Speech API.
- **Backend**: FastAPI (Python) for modular, asynchronous API services.
- **Machine Learning**: PyTorch & Torchvision (ResNet18) for computer vision tasks.
- **Storage**: Local JSON-based patient history and file-based dataset management.

## 📂 Project Structure

- `frontend/`: React source code, Voice AI logic, and responsive UI components.
- `backend/`: FastAPI application containing routes (`/analyze`) and core services.
- `model/`: PyTorch training pipeline, ResNet18 weights, and inference logic.
- `data/`: Local storage for `patient_history.json` and synthetic training datasets.

## 🔌 API Endpoints

- `POST /analyze`: The primary endpoint for submitting symptoms (text/voice) and optional images.
- `GET /health`: System health check and upload directory status.

## 🏁 Getting Started

### Backend Setup
1. Navigate to `backend/`, install dependencies: `pip install -r requirements.txt`.
2. Start server: `uvicorn app.main:app --reload`.

### Frontend Setup
1. Navigate to `frontend/`, install dependencies: `npm install`.
2. Start dev server: `npm run dev`.

---

## 🗺️ Roadmap Status

- [x] **Phase 1**: Initial Scaffolding and Backend Core.
- [x] **Phase 2**: ML Integration (ResNet18 Image Classification).
- [x] **Phase 3**: Multilingual Support (Tamil & English) and Voice AI (STT/TTS).
- [/] **Phase 4**: Secure patient profiles and dedicated Clinician Dashboard (Planned).
- [ ] **Phase 5**: Exportable PDF summaries ("Doctor Connect").

---
© 2026 MotherCare AI. All rights reserved.
