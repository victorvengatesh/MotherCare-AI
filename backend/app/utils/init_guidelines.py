# init_guidelines.py — Automatically compile and index default clinical guidelines
import os
import uuid
import hashlib
from pathlib import Path
from sqlalchemy.orm import Session
from app.db import models
from app.utils.logger import logger

def build_default_guidelines_pdf(pdf_path: Path):
    """Compiles a detailed 12-page clinical guidelines PDF using ReportLab."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    except ImportError:
        logger.warning("ReportLab not installed. Skipping PDF build.")
        return False

    logger.info(f"Compiling default maternal health guidelines PDF at: {pdf_path}")
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        spaceAfter=15,
        textColor='#247576'
    )
    h2_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        spaceAfter=10,
        textColor='#1e293b'
    )
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        spaceAfter=8
    )

    story = []
    
    # Page 1: Cover & Intro
    story.append(Paragraph("MotherCare AI Clinical Guidelines", title_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>Version:</b> 1.0.0<br/><b>Reference:</b> WHO Maternal & Newborn Care Guidelines", body_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph("This document contains clinical guidelines on maternal care, gestational milestones, high-risk screening, and baby care for decision support.", body_style))
    story.append(PageBreak())
    
    # Page 2: Trimester Milestones
    story.append(Paragraph("Trimester Milestones & Physiological Shifts", h2_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>First Trimester (Weeks 1-12):</b> Focus on embryonic development, organogenesis. Core symptoms include nausea, fatigue, and breast tenderness. Heavy bleeding or severe unilateral lower pain indicates ectopic pregnancy or early miscarriage risk.", body_style))
    story.append(Paragraph("<b>Second Trimester (Weeks 13-26):</b> Quickening (fetal movement) begins. Gestational diabetes screening occurs between weeks 24-28. Check blood pressure for signs of early onset pre-eclampsia.", body_style))
    story.append(Paragraph("<b>Third Trimester (Weeks 27-40):</b> Watch for symptoms of pre-eclampsia (blurred vision, severe headaches, hands swelling). Standard fetal movement check (kick counts) should count at least 10 kicks in 2 hours.", body_style))
    story.append(PageBreak())
    
    # Page 3: High-Risk Pregnancies
    story.append(Paragraph("High-Risk Pregnancy Screening & Management", h2_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Advanced Maternal Age (35+):</b> Increased risk of chromosomal abnormalities, gestational diabetes, and gestational hypertension. Require regular clinical review.", body_style))
    story.append(Paragraph("<b>Multiple Pregnancy (Twins/Triplets):</b> Higher risk of preterm birth, twin-to-twin transfusion syndrome, and pre-eclampsia. Monitor cervical length and blood pressure.", body_style))
    story.append(Paragraph("<b>Pre-existing Conditions:</b> Chronic hypertension, type 1/2 diabetes, thyroid disorders, and cardiorespiratory diseases require co-management with specialists.", body_style))
    story.append(PageBreak())
    
    # Page 4: Nutrition & Diet
    story.append(Paragraph("Prenatal Nutrition & Weight Gain Guidance", h2_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Iron & Folate:</b> Essential for red blood cell synthesis and prevention of neural tube defects. Daily intake of 400mcg of folic acid and 27mg of iron is recommended. Eat leafy greens, beans, and lean meats.", body_style))
    story.append(Paragraph("<b>Calcium & Vitamin D:</b> Vital for fetal bone mineralization. Daily requirement: 1000mg calcium. Sources: dairy, fortified juices, and tofu.", body_style))
    story.append(Paragraph("<b>Weight Gain:</b> Healthy weight gain depends on pre-pregnancy BMI. Underweight (28-40 lbs), normal weight (25-35 lbs), overweight (15-25 lbs), obese (11-20 lbs). Do not restrict calories.", body_style))
    story.append(PageBreak())
    
    # Page 5: Exercise & Activity
    story.append(Paragraph("Exercise & Physical Activity Guidelines", h2_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Recommended Activity:</b> 150 minutes of moderate aerobic exercise per week. Walking, swimming, prenatal yoga, and stationary cycling are safe.", body_style))
    story.append(Paragraph("<b>Warning Signs to Stop:</b> Chest pain, dizziness, vaginal bleeding, fluid leakage, or painful uterine contractions.", body_style))
    story.append(Paragraph("<b>Contraindications:</b> Avoid high-impact sports, contact activities, or lying flat on your back after the first trimester.", body_style))
    story.append(PageBreak())
    
    # Page 6: Medication Safety
    story.append(Paragraph("Medication Safety & Contraindications", h2_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>FDA Pregnancy Categories:</b> Category A (Safe, e.g. levothyroxine), Category B (Generally Safe, e.g. paracetamol), Category C (Caution, e.g. steroids), Category D (Avoid unless critical, e.g. lisinopril), Category X (Contraindicated, e.g. isotretinoin).", body_style))
    story.append(Paragraph("<b>Common OTCs:</b> Paracetamol is first-line for pain. Avoid NSAIDs (ibuprofen, aspirin) in the third trimester as they can cause premature closure of the fetal ductus arteriosus.", body_style))
    story.append(Paragraph("<b>Chronic Meds:</b> Do not stop chronic disease treatments (asthma, seizures, hypertension) without consulting your physician.", body_style))
    story.append(PageBreak())
    
    # Page 7: Vaccinations
    story.append(Paragraph("Immunization & Vaccinations", h2_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Influenza Vaccine:</b> Safe and highly recommended in any trimester during flu season. Protects both mother and baby.", body_style))
    story.append(Paragraph("<b>Tdap Vaccine:</b> Recommended between weeks 27-36 to pass passive pertussis immunity to the newborn.", body_style))
    story.append(Paragraph("<b>Contraindicated Vaccines:</b> Avoid live vaccines (MMR, Varicella, Yellow Fever) due to theoretical risk of viral transmission to the fetus.", body_style))
    story.append(PageBreak())
    
    # Page 8: Labor Warning Signs
    story.append(Paragraph("Warning Signs & Labor Markers", h2_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Water Breaking (PROM):</b> Sudden gush or continuous trickle of clear/pink fluid. Go to maternity triage immediately to prevent infection.", body_style))
    story.append(Paragraph("<b>Regular Contractions:</b> Contractions occurring every 5 minutes, lasting 60 seconds, for at least 1 hour (5-1-1 rule) indicate active labor.", body_style))
    story.append(Paragraph("<b>Red Flags:</b> Bleeding like a period, severe constant pain, lack of baby movement, or blurred vision with headache require emergency care.", body_style))
    story.append(PageBreak())
    
    # Page 9: Delivery Preparation
    story.append(Paragraph("Delivery & Pain Relief Options", h2_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Epidural Anesthesia:</b> Highly effective regional pain block. Administered in active labor. Slows labor transiently, can cause blood pressure drops.", body_style))
    story.append(Paragraph("<b>Cesarean Section:</b> Scheduled or emergency surgical delivery. Requires spinal block or general anesthesia. Recovery takes 4-6 weeks.", body_style))
    story.append(Paragraph("<b>Birthing Positions:</b> Squatting, side-lying, or semi-reclined can aid maternal comfort and fetal descent.", body_style))
    story.append(PageBreak())
    
    # Page 10: Breastfeeding
    story.append(Paragraph("Breastfeeding & Lactation Support", h2_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Colostrum:</b> The yellow early milk rich in antibodies. Essential for baby's immune system.", body_style))
    story.append(Paragraph("<b>Proper Latch:</b> Wide open mouth covering both the nipple and most of the areola prevents sore nipples and ensures milk flow.", body_style))
    story.append(Paragraph("<b>Mastitis:</b> Breast engorgement leading to infection. Symptoms: painful red breast and fever. Requires continuous empty breastfeeding and antibiotics.", body_style))
    story.append(PageBreak())
    
    # Page 11: Postpartum Recovery
    story.append(Paragraph("Postpartum Care & Warning Signs", h2_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Lochia (Bleeding):</b> Normal bleeding lasting up to 6 weeks. Should change from bright red to brown, then yellowish. If soaking a pad per hour, seek immediate emergency help.", body_style))
    story.append(Paragraph("<b>Postpartum Depression (PPD):</b> Sadness, anxiety, or fatigue that interferes with daily care. Differentiate from transient baby blues. Seek immediate help if suicidal.", body_style))
    story.append(Paragraph("<b>C-Section Incision:</b> Keep clean and dry. Watch for redness, swelling, or foul drainage indicating infection.", body_style))
    story.append(PageBreak())
    
    # Page 12: Newborn Care
    story.append(Paragraph("Newborn Care & Vital Signs", h2_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Feeding Frequency:</b> Every 2-3 hours (8-12 times a day) for breastfed newborns.", body_style))
    story.append(Paragraph("<b>Jaundice:</b> Yellowing of skin/eyes. Mild is common. Severe jaundice requires phototherapy to prevent brain damage.", body_style))
    story.append(Paragraph("<b>Warning Signs:</b> Fever (rectal temp > 100.4F), difficulty breathing, poor feeding, or extreme lethargy.", body_style))

    doc.build(story)
    logger.info("Default guidelines PDF built successfully!")
    return True


def auto_index_default_guidelines(db: Session):
    """Checks the database and indexes default guidelines if empty."""
    # Check if guidelines are already loaded
    doc_count = db.query(models.RAGDocument).count()
    if doc_count > 0:
        return
        
    logger.info("No guidelines found in database. Setting up default clinical guidelines...")
    
    # Generate default PDF path
    base_dir = Path(__file__).resolve().parent.parent.parent
    uploads_dir = base_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = uploads_dir / "maternal_health_guidelines_v1.pdf"
    
    # Build the PDF
    build_default_guidelines_pdf(pdf_path)
    
    if not pdf_path.exists():
        logger.error("Failed to find or build guidelines PDF. Skipping indexing.")
        return
        
    # Read PDF hash
    with open(pdf_path, "rb") as f:
        file_hash = hashlib.md5(f.read()).hexdigest()
        
    # Add document to SQLite
    doc_id = str(uuid.uuid4())
    doc = models.RAGDocument(
        id=doc_id,
        filename=pdf_path.name,
        title="WHO Maternal Care Guidelines",
        version="1.0",
        file_hash=file_hash,
        is_active=True,
        ingestion_status="success",
        metadata_json={"description": "System-generated WHO maternal and newborn clinical guide."}
    )
    
    try:
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # Index in ChromaDB
        from app.services.rag_service import index_medical_document_page_by_page
        chunks = index_medical_document_page_by_page(
            file_path=pdf_path,
            doc_id=doc_id,
            doc_title=doc.title,
            doc_version=doc.version
        )
        logger.info(f"Successfully auto-indexed WHO guidelines document with {chunks} chunks!")
    except Exception as e:
        db.rollback()
        logger.exception("Failed to auto-index guidelines: %s", e)
