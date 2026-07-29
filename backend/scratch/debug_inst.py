from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db import models

engine = create_engine("sqlite:///./test_phase4.db")
Session = sessionmaker(bind=engine)
db = Session()

insts = db.query(models.PatientInstruction).all()
print("Total instructions in test_phase4.db:", len(insts))
for i in insts:
    print(f"ID: {i.id}, Patient: {i.patient_id}, Visible: {i.patient_visible} (type: {type(i.patient_visible)}), Status: {i.status}, Expiry: {i.expiry_date}")
