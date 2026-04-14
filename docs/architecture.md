# MotherCare AI - System Architecture

## Overview
MotherCare AI is a decoupled web application with a React frontend and a FastAPI backend. It is designed to be scalable, future-ready, and AI-first.

## Components

### Frontend (React + Vite)
- **Dashboard**: Main interactive area for symptom entry and image upload.
- **Service Layer**: Uses native `fetch` to communicate with the backend API.
- **State Management**: React `useState` for V1; easily upgradable to Context or Redux/Zustand if needed.

### Backend (FastAPI)
- **API routes**: Clean separation of concerns using `APIRouter`.
- **Services**: Business logic isolated from routing.
- **Schemas**: Strict data validation using Pydantic.
- **Async Processing**: Ready for long-running AI inference tasks.

### AI Model Pipeline
- **Storage**: Structured `model/` directory for training and inference.
- **Data Life Cycle**: `data/raw` -> `data/processed` -> Training.

## Scalability Path
1. **Database**: Ready for integration (SQLAlchemy or Tortoise ORM).
2. **Authentication**: Auth middleware can be added to the FastAPI app.
3. **Queueing**: For heavy image processing, Celery or Redis Task Queue is recommended.
4. **Multilingual**: Backend can be extended with i18n support; frontend can use `react-i18next`.
