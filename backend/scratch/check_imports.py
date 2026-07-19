import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.db import models
print("models OK")

from app.services.rag_service import get_relevant_context
print("rag_service OK")

from app.services.risk_engine import MaternalRiskEngine
print("risk_engine OK")

from app.agents.orchestrator import run_consultation
print("orchestrator OK")

from app.routes.ai import router
print("ai routes OK")

from app.main import app
print("main app OK")

print("\nALL IMPORTS PASSED")
