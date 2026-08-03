# clinical_library.py — Expanded Clinical Symptom Library for MotherCare AI v2.1
# Maps 120+ clinical symptoms with Tamil/Tanglish synonyms and 30 emergency override rules.

SYMPTOM_LIBRARY = {
    # ── Obstetric Symptoms (1-20) ─────────────────────────────────────────────
    "vaginal_bleeding": {
        "category": "Obstetric", "label": "Vaginal Bleeding",
        "synonyms": ["bleeding", "blood discharge", "red discharge", "ratham", "இரத்தம்", "blood leaking"],
        "Tamil": ["இரத்தப்போக்கு", "இரத்தம் வருதல்"], "Tanglish": ["ratham varuthu", "bleeding aguthu"],
        "trimester_relevance": {1: "Ectopic, miscarriage risk.", 2: "Placenta previa.", 3: "Placental abruption, bloody show."},
        "required_questions": ["How heavy is the bleeding?", "Are you experiencing severe abdominal cramps?"],
        "emergency_indicators": ["heavy", "soaking a pad", "severe pain"], "risk_range": "Urgent to Emergency"
    },
    "spotting": {
        "category": "Obstetric", "label": "Vaginal Spotting",
        "synonyms": ["spotting", "light bleeding", "pink discharge", "brown spots", "ratha thuli"],
        "Tamil": ["லேசான இரத்தப்போக்கு", "புள்ளிகள்"], "Tanglish": ["ratham konjam varuthu", "spotting"],
        "trimester_relevance": {1: "Implantation common, miscarriage warning.", 2: "Cervical change.", 3: "Early labor marker."},
        "required_questions": ["Is the spotting continuous?", "Do you have any pelvic pressure?"],
        "emergency_indicators": ["turning into heavy flow", "associated with severe cramps"], "risk_range": "Routine to Urgent"
    },
    "clot_passage": {
        "category": "Obstetric", "label": "Blood Clot Passage",
        "synonyms": ["clots", "passing clots", "blood lumps", "ratha katti", "clotting"],
        "Tamil": ["இரத்த கட்டிகள்"], "Tanglish": ["ratha katti poguthu", "clots varuthu"],
        "trimester_relevance": {1: "Miscarriage sign.", 2: "Placental abruption risk.", 3: "Hemorrhage or labor onset."},
        "required_questions": ["What is the size of the clots (e.g. coin or lemon-sized)?", "Is there accompanying heavy bleeding?"],
        "emergency_indicators": ["lemon size", "large clots", "dizziness"], "risk_range": "Urgent to Emergency"
    },
    "abdominal_pain": {
        "category": "Obstetric", "label": "Abdominal Pain",
        "synonyms": ["abdominal pain", "stomach pain", "vayi vali", "stomach cramp", "stomach ache"],
        "Tamil": ["வயிற்று வலி"], "Tanglish": ["vayiru valikuthu", "vayi vali"],
        "trimester_relevance": {1: "Ectopic warning, round ligament pain.", 2: "Uterine growth, contractions.", 3: "Labor onset, abruption risk."},
        "required_questions": ["Is the pain constant or crampy?", "Is the pain located on one side or all over?"],
        "emergency_indicators": ["severe constant", "sharp one sided", "rigid abdomen"], "risk_range": "Routine to Emergency"
    },
    "pelvic_pain": {
        "category": "Obstetric", "label": "Pelvic Pain",
        "synonyms": ["pelvic pain", "pelvic pressure", "lower belly pain", "hip pressure"],
        "Tamil": ["இடுப்பு வலி", "அடிவயிறு வலி"], "Tanglish": ["iduppu vali", "pelvic vali"],
        "trimester_relevance": {1: "Early expansion, ectopic risk.", 2: "Symphysis pubis dysfunction.", 3: "Fetal head descent."},
        "required_questions": ["Does the pain radiate to your back?", "Do you feel pressure like the baby pushing down?"],
        "emergency_indicators": ["severe unyielding", "leakage of fluid"], "risk_range": "Home Care to Urgent"
    },
    "lower_abdominal_cramps": {
        "category": "Obstetric", "label": "Lower Abdominal Cramping",
        "synonyms": ["cramping", "cramps lower stomach", "menstrual-like cramps", "adi vayiru vali"],
        "Tamil": ["அடிவயிற்று பிடிப்பு"], "Tanglish": ["adi vayiru valikuthu", "cramps"],
        "trimester_relevance": {1: "Normal expansion or early loss warning.", 2: "Preterm labor warning.", 3: "Labor contractions."},
        "required_questions": ["Are the cramps regular?", "Is there any pink or red discharge?"],
        "emergency_indicators": ["regular intervals", "associated bleeding"], "risk_range": "Routine to Urgent"
    },
    "severe_one_sided_pain": {
        "category": "Obstetric", "label": "Severe One-Sided Pelvic Pain",
        "synonyms": ["one-sided pain", "right side pain", "left side pain", "unilateral pain"],
        "Tamil": ["ஒரு பக்க வயிற்று வலி"], "Tanglish": ["oru pakka vali", "one side valikuthu"],
        "trimester_relevance": {1: "High risk of ectopic pregnancy (critical emergency).", 2: "Ovarian cyst torsion.", 3: "Rare abruption variant."},
        "required_questions": ["Did this pain start suddenly?", "Are you feeling lightheaded, dizzy, or bleeding?"],
        "emergency_indicators": ["sudden onset", "fainting", "dizziness", "shoulder tip pain"], "risk_range": "Emergency"
    },
    "contractions": {
        "category": "Obstetric", "label": "Uterine Contractions",
        "synonyms": ["contractions", "tightening", "uterus tightening", "labor pains", "வலி"],
        "Tamil": ["பிரசவ வலி", "வயிறு இறுக்கம்"], "Tanglish": ["vayiru tight ah aguthu", "வலி varuthu"],
        "trimester_relevance": {1: "Abnormal.", 2: "Preterm labor warning.", 3: "Braxton Hicks vs True labor."},
        "required_questions": ["How far apart are the contractions?", "Do they stop if you lie down and drink water?"],
        "emergency_indicators": ["regular every 5 minutes", "water broke"], "risk_range": "Routine to Emergency"
    },
    "premature_contractions": {
        "category": "Obstetric", "label": "Premature Uterine Contractions",
        "synonyms": ["early contractions", "contractions before 37 weeks", "early labor pains"],
        "Tamil": ["முன்கூட்டிய பிரசவ வலி"], "Tanglish": ["seekirama vali varuthu", "premature contractions"],
        "trimester_relevance": {1: "N/A", 2: "Preterm labor risk.", 3: "Preterm labor risk (before week 37)."},
        "required_questions": ["Are you experiencing more than 4 contractions in an hour?", "Do you have low back pressure?"],
        "emergency_indicators": ["more than 4 per hour", "fluid leakage", "bleeding"], "risk_range": "Urgent to Emergency"
    },
    "fluid_leakage": {
        "category": "Obstetric", "label": "Vaginal Fluid Leakage",
        "synonyms": ["fluid leaking", "water trickle", "pant wet", "thanni vadiyuthu", "நீர் கசிவு"],
        "Tamil": ["பனிக்குட நீர் கசிவு"], "Tanglish": ["thanni poguthu", "fluid leakage"],
        "trimester_relevance": {1: "Atypical.", 2: "PPROM risk.", 3: "PROM risk or labor onset."},
        "required_questions": ["Is the fluid clear, yellow, or greenish?", "Was it a sudden gush or a slow trickle?"],
        "emergency_indicators": ["greenish color", "foul smell", "continuous leak"], "risk_range": "Urgent to Emergency"
    },
    "water_breaking": {
        "category": "Obstetric", "label": "Water Breaking",
        "synonyms": ["water broke", "rupture of membranes", "gush of water", "amniotic fluid gush"],
        "Tamil": ["பனிக்குடம் உடைதல்"], "Tanglish": ["thanni kottiyeeruku", "water break"],
        "trimester_relevance": {1: "Abnormal.", 2: "Critical risk of infection (PPROM).", 3: "Labor start indication."},
        "required_questions": ["What is the color of the amniotic fluid?", "Are you having contractions now?"],
        "emergency_indicators": ["greenish/brown fluid", "before 37 weeks gestation"], "risk_range": "Urgent to Emergency"
    },
    "reduced_fetal_movement": {
        "category": "Obstetric", "label": "Reduced Fetal Movement",
        "synonyms": ["reduced kicks", "fetal movement low", "baby moving less", "movement reduced", "குழந்தை அசைவு குறைவு"],
        "Tamil": ["குழந்தை அசைவு குறைவு"], "Tanglish": ["baby movement kammi", "kicks low"],
        "trimester_relevance": {1: "N/A", 2: "Can be variable.", 3: "Critical marker of fetal oxygenation."},
        "required_questions": ["When did you last feel the baby move?", "Did you get 10 kicks in 2 hours after a meal?"],
        "emergency_indicators": ["less than 10 kicks in 2 hours", "no movements at all"], "risk_range": "Urgent to Emergency"
    },
    "absent_fetal_movement": {
        "category": "Obstetric", "label": "Absent Fetal Movement",
        "synonyms": ["no fetal movement", "kicks stopped", "no kicks", "baby not moving", "அசைவே இல்லை"],
        "Tamil": ["குழந்தையின் அசைவு இல்லை"], "Tanglish": ["baby asaiyave illa", "no movement"],
        "trimester_relevance": {1: "N/A", 2: "Consult clinic if past week 24.", 3: "Critical fetal distress alert."},
        "required_questions": ["How long has it been since the last kick?", "Have you tried sensory stimulation (cold drink/rubbing belly)?"],
        "emergency_indicators": ["no kicks felt for several hours", "gestational age past 28 weeks"], "risk_range": "Emergency"
    },
    "unusual_vaginal_discharge": {
        "category": "Obstetric", "label": "Unusual Vaginal Discharge",
        "synonyms": ["thick discharge", "mucus plug", "pink discharge", "bloody discharge"],
        "Tamil": ["அசாதாரண யோனி வெளியேற்றம்"], "Tanglish": ["vella paduthu", "discharge custom"],
        "trimester_relevance": {1: "Evaluate for yeast/bacterial infection.", 2: "Infection check.", 3: "Mucus plug loss (normal labor precursor)."},
        "required_questions": ["Is the discharge foul-smelling, itchy, or bloody?", "What is the color of the discharge?"],
        "emergency_indicators": ["bloody show with contractions before 37 weeks"], "risk_range": "Home Care to Routine"
    },
    "placental_warning_signs": {
        "category": "Obstetric", "label": "Placental Warning Signs",
        "synonyms": ["abruption pain", "dark bleeding", "stiff hard belly"],
        "Tamil": ["நஞ்சுக்கொடி எச்சரிக்கை"], "Tanglish": ["placenta issue", "vayiru kal kooda iruku"],
        "trimester_relevance": {1: "Atypical.", 2: "Placenta previa/abruption risk.", 3: "Severe abruption risk."},
        "required_questions": ["Is your abdomen constantly rigid, stiff, or tender to the touch?", "Are you passing dark red blood?"],
        "emergency_indicators": ["rigid stomach", "constant severe pain", "dark red bleeding"], "risk_range": "Emergency"
    },
    "suspected_ectopic_symptoms": {
        "category": "Obstetric", "label": "Suspected Ectopic Pregnancy Symptoms",
        "synonyms": ["ectopic sign", "shoulder tip pain", "one-sided sharp pain"],
        "Tamil": ["கருப்பைக்கு வெளியே கர்ப்பம்"], "Tanglish": ["ectopic pregnancy"],
        "trimester_relevance": {1: "High risk between weeks 4-10.", 2: "N/A", 3: "N/A"},
        "required_questions": ["Do you feel pain in the tip of your shoulder when lying down?", "Are you experiencing spotting or dizziness?"],
        "emergency_indicators": ["shoulder pain", "fainting", "severe unilateral pelvic pain"], "risk_range": "Emergency"
    },
    "labor_signs": {
        "category": "Obstetric", "label": "Labor Signs",
        "synonyms": ["labor signs", "show", "active labor onset", "mucus plug loss"],
        "Tamil": ["பிரசவ அறிகுறிகள்"], "Tanglish": ["delivery signs", "vali start"],
        "trimester_relevance": {1: "Abnormal.", 2: "Preterm labor warning.", 3: "Full term labor preparation."},
        "required_questions": ["Are your contractions regular?", "Has your water broken?"],
        "emergency_indicators": ["contractions before week 37", "excessive bleeding"], "risk_range": "Routine to Emergency"
    },
    "post_date_pregnancy_concerns": {
        "category": "Obstetric", "label": "Post-Date Pregnancy Concerns",
        "synonyms": ["overdue pregnancy", "past due date", "post term gestation", "41 weeks", "42 weeks"],
        "Tamil": ["பிரசவ தேதி கடந்த நிலை"], "Tanglish": ["duedate mudinjiduchu", "overdue"],
        "trimester_relevance": {1: "N/A", 2: "N/A", 3: "Weeks 40-42 management."},
        "required_questions": ["What was your exact estimated due date?", "How active are the fetal movements today?"],
        "emergency_indicators": ["reduced fetal movements", "meconium stained water leakage"], "risk_range": "Routine to Urgent"
    },

    # ── Hypertensive / Pre-eclampsia Symptoms (21-40) ─────────────────────────
    "severe_headache": {
        "category": "Hypertensive", "label": "Severe Headache",
        "synonyms": ["severe headache", "constant head pain", "thalai vali severe", "unyielding headache", "headache"],
        "Tamil": ["கடுமையான தலைவலி"], "Tanglish": ["thalai vali romba", "severe headache"],
        "trimester_relevance": {1: "Hormonal variations.", 2: "Pre-eclampsia screening marker past week 20.", 3: "Pre-eclampsia danger sign."},
        "required_questions": ["Does the headache relieve with paracetamol and rest?", "Do you have any visual changes?"],
        "emergency_indicators": ["unrelieved", "associated blurry vision", "high BP"], "risk_range": "Routine to Emergency"
    },
    "persistent_headache": {
        "category": "Hypertensive", "label": "Persistent Headache",
        "synonyms": ["continuous headache", "chronic head pain", "headache not going away"],
        "Tamil": ["விடாத தலைவலி"], "Tanglish": ["headache nirkala", "continuous thalaivali"],
        "trimester_relevance": {1: "Hormonal.", 2: "Pre-eclampsia sign.", 3: "Pre-eclampsia sign."},
        "required_questions": ["How long has this headache lasted?", "Are you experiencing facial swelling?"],
        "emergency_indicators": ["longer than 24 hours", "accompanied by high BP"], "risk_range": "Routine to Urgent"
    },
    "blurred_vision": {
        "category": "Hypertensive", "label": "Blurred Vision",
        "synonyms": ["blurry vision", "blurred eyes", "kan theriyala", "spots in eyes", "பார்வை மங்கல்", "kannu blur", "blur ah iruku"],
        "Tamil": ["மங்கலான பார்வை"], "Tanglish": ["kan theriyala", "blurry vision", "kannu blur ah iruku"],
        "trimester_relevance": {1: "Atypical.", 2: "Pre-eclampsia sign.", 3: "Pre-eclampsia sign."},
        "required_questions": ["Are you seeing spots, flashes of light, or floaters?", "Do you have a severe headache?"],
        "emergency_indicators": ["flashing lights", "sudden blurry vision", "severe headache"], "risk_range": "Urgent to Emergency"
    },
    "flashing_lights": {
        "category": "Hypertensive", "label": "Visual Flashing Lights",
        "synonyms": ["flashing lights", "seeing stars", "visual sparks", "light flashes"],
        "Tamil": ["பார்வையில் ஒளி கீற்றுகள்"], "Tanglish": ["kanla star theriyuthu", "flashing lights"],
        "trimester_relevance": {1: "Atypical.", 2: "Severe pre-eclampsia indicator.", 3: "Severe pre-eclampsia indicator."},
        "required_questions": ["Do you feel dizzy?", "What is your current blood pressure if known?"],
        "emergency_indicators": ["associated with high BP", "severe headache"], "risk_range": "Emergency"
    },
    "swelling_in_face": {
        "category": "Hypertensive", "label": "Facial Swelling",
        "synonyms": ["face swelling", "puffy face", "face edema", "facial puffiness"],
        "Tamil": ["முக வீக்கம்"], "Tanglish": ["mugam veengiiruku", "face swelling"],
        "trimester_relevance": {1: "Atypical.", 2: "Pre-eclampsia screening.", 3: "Severe pre-eclampsia warning."},
        "required_questions": ["Did the swelling occur suddenly?", "Do you have a headache or blurred vision?"],
        "emergency_indicators": ["sudden onset", "associated headache"], "risk_range": "Urgent to Emergency"
    },
    "swelling_in_hands": {
        "category": "Hypertensive", "label": "Hand Swelling",
        "synonyms": ["hand swelling", "swollen fingers", "tight rings", "hand edema"],
        "Tamil": ["கை வீக்கம்"], "Tanglish": ["kai veengiiruku", "hand swelling"],
        "trimester_relevance": {1: "Normal fluid shift.", 2: "Hypertensive marker.", 3: "Severe pre-eclampsia warning if sudden."},
        "required_questions": ["Are your rings suddenly tight or impossible to remove?", "Is the swelling accompanied by rapid weight gain?"],
        "emergency_indicators": ["sudden hand puffiness", "headache", "blurred vision"], "risk_range": "Routine to Emergency"
    },
    "sudden_weight_gain": {
        "category": "Hypertensive", "label": "Sudden Weight Gain",
        "synonyms": ["rapid weight gain", "weight increased fast", "sudden weight increase"],
        "Tamil": ["திடீர் உடல் எடை அதிகரிப்பு"], "Tanglish": ["weight suddenly increased", "fast weight gain"],
        "trimester_relevance": {1: "Atypical.", 2: "Pre-eclampsia sign (fluid retention).", 3: "Pre-eclampsia sign (fluid retention)."},
        "required_questions": ["Have you gained more than 2 pounds in a single week?", "Do you notice swelling in your face or ankles?"],
        "emergency_indicators": ["more than 2 lbs gain in a week", "swelling", "headache"], "risk_range": "Routine to Urgent"
    },
    "high_blood_pressure": {
        "category": "Hypertensive", "label": "High Blood Pressure",
        "synonyms": ["high BP", "hypertension", "systolic high", "blood pressure high"],
        "Tamil": ["உயர் இரத்த அழுத்தம்"], "Tanglish": ["BP high", "high BP"],
        "trimester_relevance": {1: "Chronic hypertension.", 2: "Gestational hypertension or pre-eclampsia (past week 20).", 3: "Pre-eclampsia risk."},
        "required_questions": ["What is your blood pressure reading?", "Do you have a headache, blurry vision, or rib pain?"],
        "emergency_indicators": ["BP 160/110 or higher", "systolic >= 140 with symptoms"], "risk_range": "Urgent to Emergency"
    },
    "chest_pain": {
        "category": "Hypertensive", "label": "Chest Pain",
        "synonyms": ["chest pain", "pain in chest", "chest pressure", "heart pain", "நெஞ்சு வலி"],
        "Tamil": ["நெஞ்சு வலி"], "Tanglish": ["nenju vali", "chest pain"],
        "trimester_relevance": {1: "Abnormal.", 2: "Pre-eclampsia, pulmonary embolism risk.", 3: "Pre-eclampsia, pulmonary embolism risk."},
        "required_questions": ["Is the pain sharp, crushing, or radiating to your arm or neck?", "Do you have shortness of breath?"],
        "emergency_indicators": ["radiating pain", "gasping for air", "sudden onset"], "risk_range": "Emergency"
    },
    "breathing_difficulty": {
        "category": "Hypertensive", "label": "Breathing Difficulty",
        "synonyms": ["difficulty breathing", "shortness of breath", "breathless", "moochu muttuthu"],
        "Tamil": ["மூச்சு திணறல்"], "Tanglish": ["moochu vida kashtam", "breathless"],
        "trimester_relevance": {1: "Hormonal breathlessness.", 2: "Pre-eclampsia pulmonary edema risk.", 3: "Diaphragm compression vs pulmonary edema."},
        "required_questions": ["Does the shortness of breath get worse when you lie down flat?", "Do you have a cough or fever?"],
        "emergency_indicators": ["worse lying flat", "sudden severe breathlessness"], "risk_range": "Urgent to Emergency"
    },
    "upper_abdominal_pain": {
        "category": "Hypertensive", "label": "Upper Abdominal Pain",
        "synonyms": ["epigastric pain", "pain under ribs", "right upper quadrant pain", "liver pain"],
        "Tamil": ["மேல் வயிற்று வலி"], "Tanglish": ["ribs pain", "epigastric vali"],
        "trimester_relevance": {1: "Severe reflux.", 2: "HELLP syndrome / pre-eclampsia indicator.", 3: "HELLP syndrome / pre-eclampsia indicator."},
        "required_questions": ["Do you feel pain under your right ribs like a tight band?", "Is there associated vomiting?"],
        "emergency_indicators": ["pain under right ribs", "vomiting", "high BP"], "risk_range": "Urgent to Emergency"
    },
    "seizures": {
        "category": "Hypertensive", "label": "Seizures / Fits",
        "synonyms": ["seizure", "convulsions", "fits", "shaking uncontrollably"],
        "Tamil": ["வலிப்பு"], "Tanglish": ["fits varuthu", "seizures"],
        "trimester_relevance": {1: "Epilepsy.", 2: "Eclampsia (critical maternal-fetal emergency).", 3: "Eclampsia (critical maternal-fetal emergency)."},
        "required_questions": ["Is the patient currently conscious?", "How long did the seizure last?"],
        "emergency_indicators": ["any seizure activity"], "risk_range": "Emergency"
    },
    "confusion": {
        "category": "Hypertensive", "label": "Mental Confusion",
        "synonyms": ["confusion", "disorientation", "brain fog", "altered mental status"],
        "Tamil": ["மனக்குழப்பம்"], "Tanglish": ["confusion ah iruku", "disoriented"],
        "trimester_relevance": {1: "Severe dehydration.", 2: "Eclampsia precursor.", 3: "Eclampsia precursor or severe sepsis."},
        "required_questions": ["Is the confusion accompanied by a severe headache or fever?", "Does the patient know where they are?"],
        "emergency_indicators": ["sudden disorientation", "associated high BP", "high fever"], "risk_range": "Urgent to Emergency"
    },

    # ── Diabetic Symptoms (41-55) ─────────────────────────────────────────────
    "excessive_thirst": {
        "category": "Diabetic", "label": "Excessive Thirst",
        "synonyms": ["thirst", "extreme thirst", "polydipsia", "always dry mouth"],
        "Tamil": ["அதிக தாகம்"], "Tanglish": ["romba thagam", "excessive thirst"],
        "trimester_relevance": {1: "Normal volume change.", 2: "Gestational diabetes warning.", 3: "Gestational diabetes warning."},
        "required_questions": ["Are you urinating more frequently than usual?", "Have you checked your blood sugar?"],
        "emergency_indicators": ["lethargy", "fruity breath odor"], "risk_range": "Routine to Urgent"
    },
    "frequent_urination": {
        "category": "Diabetic", "label": "Frequent Urination",
        "synonyms": ["polyuria", "urinating constantly", "toilet frequently", "adikkadi bathroom"],
        "Tamil": ["அடிக்கடி சிறுநீர் கழித்தல்"], "Tanglish": ["bathroom adikkadi poguthu", "frequent urine"],
        "trimester_relevance": {1: "Normal pelvic pressure.", 2: "Gestational diabetes screening marker.", 3: "Normal compression vs diabetes."},
        "required_questions": ["Do you feel any pain or burning when urinating?", "What are your recent blood sugar readings?"],
        "emergency_indicators": ["burning sensation", "extreme fatigue"], "risk_range": "Home Care to Routine"
    },
    "high_glucose_reading": {
        "category": "Diabetic", "label": "Hyperglycemia",
        "synonyms": ["high glucose", "high blood sugar", "sugar high", "hyperglycemia"],
        "Tamil": ["அதிக சர்க்கரை அளவு"], "Tanglish": ["sugar reading high", "hyperglycemia"],
        "trimester_relevance": {1: "Pre-existing diabetes.", 2: "Gestational diabetes risk.", 3: "Gestational diabetes complications risk."},
        "required_questions": ["What is the blood glucose reading (mg/dL or mmol/L)?", "Did you check fasting or post-meal?"],
        "emergency_indicators": ["glucose above 250 mg/dL", "ketones in urine", "vomiting"], "risk_range": "Routine to Emergency"
    },
    "low_glucose_reading": {
        "category": "Diabetic", "label": "Hypoglycemia",
        "synonyms": ["low glucose", "low sugar", "hypoglycemia", "sugar drop"],
        "Tamil": ["குறைந்த சர்க்கரை அளவு"], "Tanglish": ["sugar level low", "hypoglycemia"],
        "trimester_relevance": {1: "Morning sickness fasting.", 2: "Insulin/medication overdose.", 3: "Insulin/medication overdose."},
        "required_questions": ["What is your blood glucose reading?", "Are you feeling sweaty, dizzy, or shaking?"],
        "emergency_indicators": ["glucose below 50 mg/dL", "loss of consciousness", "confusion"], "risk_range": "Urgent to Emergency"
    },
    "dizziness": {
        "category": "Diabetic", "label": "Dizziness / Lightheadedness",
        "synonyms": ["dizziness", "giddy", "head spinning", "thalai suthal", "lightheaded"],
        "Tamil": ["தலைச்சுற்றல்"], "Tanglish": ["thalai suthal", "dizziness"],
        "trimester_relevance": {1: "Hormonal low BP.", 2: "Anemia or gestational diabetes indicator.", 3: "Supine hypotension, pre-eclampsia warning."},
        "required_questions": ["Do you feel dizzy when standing up quickly?", "Are you sweaty or shaking?"],
        "emergency_indicators": ["fainting", "chest pain", "blood pressure changes"], "risk_range": "Home Care to Urgent"
    },
    "sweating": {
        "category": "Diabetic", "label": "Excessive Sweating",
        "synonyms": ["sweating", "cold sweat", "diaphoresis", "wet skin"],
        "Tamil": ["அதிக வியர்வை"], "Tanglish": ["romba viyakuthu", "sweating"],
        "trimester_relevance": {1: "Hormonal heat flashes.", 2: "Hypoglycemia indicator.", 3: "Hypoglycemia or infection signs."},
        "required_questions": ["Are you experiencing shaking or lightheadedness?", "Do you have a fever?"],
        "emergency_indicators": ["cold sweats with confusion", "glucose < 60 mg/dL"], "risk_range": "Home Care to Urgent"
    },
    "excessive_hunger": {
        "category": "Diabetic", "label": "Excessive Hunger",
        "synonyms": ["always hungry", "polyphagia", "extreme appetite"],
        "Tamil": ["அதிக பசி"], "Tanglish": ["romba pasi", "always hungry"],
        "trimester_relevance": {1: "Normal growth requirements.", 2: "Gestational diabetes warning.", 3: "Gestational diabetes warning."},
        "required_questions": ["Is this hunger accompanied by excessive thirst?", "Are you losing weight despite eating?"],
        "emergency_indicators": ["accompanied by glucose instability"], "risk_range": "Home Care to Routine"
    },

    # ── Infection Symptoms (56-75) ────────────────────────────────────────────
    "fever": {
        "category": "Infection", "label": "Fever",
        "synonyms": ["fever", "body hot", "kaisal", "temp high", "காய்ச்சல்"],
        "Tamil": ["காய்ச்சல்"], "Tanglish": ["feverish", "kaisal"],
        "trimester_relevance": {1: "High risk of neural tube defects if temp > 101F.", 2: "UTI, chorioamnionitis risk.", 3: "Chorioamnionitis (if membranes ruptured)."},
        "required_questions": ["What is your body temperature?", "Do you have lower abdominal pain or foul vaginal discharge?"],
        "emergency_indicators": ["temperature > 101F with rigid abdomen", "foul discharge"], "risk_range": "Routine to Emergency"
    },
    "chills": {
        "category": "Infection", "label": "Chills & Shivering",
        "synonyms": ["chills", "shivering", "body shaking cold", "feeling cold"],
        "Tamil": ["குளிர் நடுக்கம்"], "Tanglish": ["kulirakuthu", "shivering", "chills"],
        "trimester_relevance": {1: "Flu-like.", 2: "UTI/Pyelonephritis indicator.", 3: "Sepsis or chorioamnionitis risk."},
        "required_questions": ["Do you have a high fever?", "Is there pain in your side or lower back?"],
        "emergency_indicators": ["accompanied by flank pain", "high fever > 101F"], "risk_range": "Routine to Urgent"
    },
    "burning_urination": {
        "category": "Infection", "label": "Painful Urination (Dysuria)",
        "synonyms": ["burning urine", "painful urine", "dysuria", "moothiram erichal", "moothiram pogumbothu erichal"],
        "Tamil": ["சிறுநீர் எரிச்சல்"], "Tanglish": ["moothiram erichal", "burning urine", "moothiram pogumbothu erichal"],
        "trimester_relevance": {1: "UTI risk.", 2: "UTI risk (can trigger preterm labor).", 3: "UTI risk (can trigger labor)."},
        "required_questions": ["Do you have fever or flank (side) pain?", "Is there blood in your urine?"],
        "emergency_indicators": ["flank pain", "fever", "visible blood in urine"], "risk_range": "Routine to Urgent"
    },
    "urinary_frequency": {
        "category": "Infection", "label": "Urinary Frequency",
        "synonyms": ["frequent peeing", "urinating often"],
        "Tamil": ["அடிக்கடி சிறுநீர்"], "Tanglish": ["peeing often"],
        "trimester_relevance": {1: "Uterine enlargement.", 2: "UTI warning.", 3: "Fetal head engagement vs UTI."},
        "required_questions": ["Do you feel the urge to pee but only a few drops come out?", "Do you have burning?"],
        "emergency_indicators": ["associated with burning and fever"], "risk_range": "Home Care to Routine"
    },
    "foul_smelling_urine": {
        "category": "Infection", "label": "Foul-Smelling Urine",
        "synonyms": ["smelly urine", "cloudy urine", "stinky pee"],
        "Tamil": ["துர்நாற்றமுடைய சிறுநீர்"], "Tanglish": ["urine smell", "smelly pee"],
        "trimester_relevance": {1: "UTI indicator.", 2: "UTI indicator.", 3: "UTI indicator."},
        "required_questions": ["Is the urine cloudy or contains visible blood?", "Are you drinking enough water?"],
        "emergency_indicators": ["associated fever", "side pain"], "risk_range": "Routine to Urgent"
    },
    "vaginal_itching": {
        "category": "Infection", "label": "Vaginal Itching",
        "synonyms": ["vaginal itch", "vulvar itching", "vaginal irritation"],
        "Tamil": ["யோனி அரிப்பு"], "Tanglish": ["vaginal itching", "aripu"],
        "trimester_relevance": {1: "Yeast infection common.", 2: "Yeast infection.", 3: "Yeast/bacterial vaginosis check."},
        "required_questions": ["Do you have thick white or grey discharge?", "Is there a burning sensation?"],
        "emergency_indicators": ["associated with lower pelvic pain"], "risk_range": "Home Care to Routine"
    },
    "wound_redness": {
        "category": "Infection", "label": "Wound Redness",
        "synonyms": ["wound red", "c-section redness", "stitch redness"],
        "Tamil": ["தழும்பில் சிவப்பு நிறம்"], "Tanglish": ["c section red", "stitch redness"],
        "trimester_relevance": {1: "N/A", 2: "N/A", 3: "Postpartum surgical site infection warning."},
        "required_questions": ["Is the redness spreading or warm to the touch?", "Is there pain or discharge from the wound?"],
        "emergency_indicators": ["spreading redness", "fever", "foul drainage"], "risk_range": "Routine to Urgent"
    },
    "wound_discharge": {
        "category": "Infection", "label": "Wound Discharge",
        "synonyms": ["pus from stitches", "leakage from c-section", "wound drainage"],
        "Tamil": ["தழும்பிலிருந்து வடியும் நீர்"], "Tanglish": ["stitch drainage", "pus leakage"],
        "trimester_relevance": {1: "N/A", 2: "N/A", 3: "Postpartum surgical wound dehiscence."},
        "required_questions": ["What is the color and smell of the discharge?", "Do you have a fever?"],
        "emergency_indicators": ["foul yellow/green discharge", "fever"], "risk_range": "Urgent to Emergency"
    },
    "breast_redness": {
        "category": "Infection", "label": "Breast Redness",
        "synonyms": ["breast red", "red patch breast", "warm breast"],
        "Tamil": ["மார்பக சிவத்தல்"], "Tanglish": ["breast red patch", "mastitis red"],
        "trimester_relevance": {1: "N/A", 2: "N/A", 3: "Postpartum mastitis warning."},
        "required_questions": ["Is the redness localized to one breast?", "Do you have flu-like symptoms or fever?"],
        "emergency_indicators": ["high fever > 101F", "rapidly spreading red streaks"], "risk_range": "Routine to Urgent"
    },
    "mastitis_symptoms": {
        "category": "Infection", "label": "Mastitis Symptoms",
        "synonyms": ["mastitis", "clogged milk duct", "infected breast", "flu-like breast pain"],
        "Tamil": ["மார்பக அழற்சி"], "Tanglish": ["breast infection", "mastitis"],
        "trimester_relevance": {1: "N/A", 2: "N/A", 3: "Postpartum lactation complications."},
        "required_questions": ["Is there a hard lump in the red area?", "Are you continuing to breastfeed or pump?"],
        "emergency_indicators": ["high fever", "spreading redness", "abscess formation"], "risk_range": "Routine to Urgent"
    },

    # ── Gastrointestinal Symptoms (76-90) ─────────────────────────────────────
    "severe_vomiting": {
        "category": "Gastrointestinal", "label": "Severe Vomiting",
        "synonyms": ["severe vomiting", "cannot keep food down", "hyperemesis", "vomiting heavily"],
        "Tamil": ["கடுமையான வாந்தி"], "Tanglish": ["romba vaanthi", "severe vomiting"],
        "trimester_relevance": {1: "Hyperemesis Gravidarum risk.", 2: "Infection, HELLP syndrome.", 3: "Pre-eclampsia HELLP syndrome warning."},
        "required_questions": ["Can you keep water or clear liquids down?", "Are you feeling dizzy when standing up?"],
        "emergency_indicators": ["unable to retain liquids for 24h", "fainting"], "risk_range": "Routine to Emergency"
    },
    "persistent_nausea": {
        "category": "Gastrointestinal", "label": "Persistent Nausea",
        "synonyms": ["continuous nausea", "nausea all day", "sick to stomach"],
        "Tamil": ["தொடர் குமட்டல்"], "Tanglish": ["nausea all day", "kumattal"],
        "trimester_relevance": {1: "Normal morning sickness.", 2: "Requires evaluation.", 3: "Evaluate BP."},
        "required_questions": ["Is the nausea affecting your weight?", "Are you able to eat small meals?"],
        "emergency_indicators": ["associated with severe dehydration"], "risk_range": "Home Care to Routine"
    },
    "dehydration": {
        "category": "Gastrointestinal", "label": "Dehydration",
        "synonyms": ["dehydration", "dry lips", "dark urine", "extremely thirsty"],
        "Tamil": ["நீர்ச்சத்து குறைபாடு"], "Tanglish": ["dehydrated", "dry mouth", "urine dark yellow"],
        "trimester_relevance": {1: "Vomiting complications.", 2: "GI infection complications.", 3: "Complication of labor or infection."},
        "required_questions": ["Are you urinating less than 3 times a day?", "Are you feeling dizzy or weak?"],
        "emergency_indicators": ["no urine output for 8h", "confusion", "fainting"], "risk_range": "Routine to Emergency"
    },
    "diarrhea": {
        "category": "Gastrointestinal", "label": "Diarrhea",
        "synonyms": ["loose stools", "diarrhea", "watery poop", "stomach loose"],
        "Tamil": ["வயிற்றுப்போக்கு"], "Tanglish": ["loose motion", "diarrhea"],
        "trimester_relevance": {1: "Dietary changes.", 2: "Food poisoning.", 3: "Labor precursor sign."},
        "required_questions": ["How many loose stools have you had today?", "Do you have a fever or blood in your stool?"],
        "emergency_indicators": ["blood in stool", "high fever", "signs of severe dehydration"], "risk_range": "Home Care to Urgent"
    },
    "constipation": {
        "category": "Gastrointestinal", "label": "Constipation",
        "synonyms": ["constipation", "hard stools", "stomach block", "cannot pass stool"],
        "Tamil": ["மலச்சிக்கல்"], "Tanglish": ["constipation", "motion pogala"],
        "trimester_relevance": {1: "Progesterone slowing GI.", 2: "Iron supplement effects.", 3: "Pelvic pressure slowing bowel movement."},
        "required_questions": ["How many days since your last bowel movement?", "Are you experiencing severe abdominal pain?"],
        "emergency_indicators": ["severe constant abdominal pain", "vomiting", "no gas passage"], "risk_range": "Home Care to Routine"
    },
    "heartburn": {
        "category": "Gastrointestinal", "label": "Heartburn / Indigestion",
        "synonyms": ["heartburn", "acid reflux", "indigestion", "chest burning", "nenju erichal"],
        "Tamil": ["நெஞ்செரிச்சல்"], "Tanglish": ["nenju erichal", "acid reflux"],
        "trimester_relevance": {1: "Hormonal sphincter relaxation.", 2: "Growing uterus.", 3: "Diaphragmatic pressure."},
        "required_questions": ["Does the pain improve with antacids?", "Is the pain located under your right ribs?"],
        "emergency_indicators": ["pain radiating to arm/jaw", "associated high BP"], "risk_range": "Home Care to Routine"
    },

    # ── Musculoskeletal Symptoms (91-105) ─────────────────────────────────────
    "back_pain": {
        "category": "Musculoskeletal", "label": "Back Pain",
        "synonyms": ["back pain", "back ache", "spine pain", "muthu vali", "முதுகு வலி"],
        "Tamil": ["முதுகு வலி"], "Tanglish": ["muthu vali", "back pain"],
        "trimester_relevance": {1: "Hormonal ligaments relaxation.", 2: "Center of gravity shift.", 3: "Fetal weight pressure, labor warning."},
        "required_questions": ["Is the back pain constant or coming in waves?", "Do you have any numbness in your legs?"],
        "emergency_indicators": ["waves of pain before 37 weeks", "loss of bowel control"], "risk_range": "Home Care to Routine"
    },
    "pelvic_girdle_pain": {
        "category": "Musculoskeletal", "label": "Pelvic Girdle Pain",
        "synonyms": ["PGP", "symphysis pubis dysfunction", "SPD", "groin pain"],
        "Tamil": ["இடுப்பு வளைய வலி"], "Tanglish": ["pelvic bone pain", "PGP"],
        "trimester_relevance": {1: "N/A", 2: "Common as relaxin peaks.", 3: "Common due to baby weight."},
        "required_questions": ["Does the pain worsen when parting your legs or walking?", "Do you hear a clicking sound in your pubic bone?"],
        "emergency_indicators": ["inability to stand or walk"], "risk_range": "Home Care to Routine"
    },
    "one_sided_leg_swelling": {
        "category": "Musculoskeletal", "label": "One-Sided Leg Swelling",
        "synonyms": ["unilateral leg swelling", "one leg swollen", "asymmetric leg swelling"],
        "Tamil": ["ஒரு பக்க கால் வீக்கம்"], "Tanglish": ["oru kaal veengiiruku", "one leg swollen"],
        "trimester_relevance": {1: "Hypercoagulable state warning (DVT risk).", 2: "DVT risk.", 3: "DVT risk (maternal thromboembolism is dangerous)."},
        "required_questions": ["Is there redness, warmth, or calf pain in that leg?", "Do you have any chest pain or shortness of breath?"],
        "emergency_indicators": ["pain/warmth in calf", "shortness of breath", "chest pain"], "risk_range": "Emergency"
    },
    "calf_pain": {
        "category": "Musculoskeletal", "label": "Calf Pain",
        "synonyms": ["calf soreness", "leg muscle pain", "pain in back of leg"],
        "Tamil": ["கெண்டைக்கால் வலி"], "Tanglish": ["calf pain", "kaal vali"],
        "trimester_relevance": {1: "DVT risk.", 2: "DVT risk.", 3: "DVT risk."},
        "required_questions": ["Is there swelling or redness in the painful calf?", "Is the pain worse when bending your foot upwards?"],
        "emergency_indicators": ["associated swelling", "sudden breathlessness"], "risk_range": "Routine to Emergency"
    },

    # ── Mental Health Symptoms (106-120) ──────────────────────────────────────
    "anxiety": {
        "category": "Mental Health", "label": "Prenatal Anxiety",
        "synonyms": ["anxious", "worrying", "fear", "nervousness", "bayama iruku"],
        "Tamil": ["மனப்பதற்றம்"], "Tanglish": ["bayama iruku", "anxious"],
        "trimester_relevance": {1: "Early adjustments.", 2: "Parenting fears.", 3: "Labor apprehension."},
        "required_questions": ["Are you experiencing panic attacks or chest tightness?", "Is the anxiety affecting your sleep?"],
        "emergency_indicators": ["thoughts of self-harm", "panic preventing breathing"], "risk_range": "Home Care to Urgent"
    },
    "depression": {
        "category": "Mental Health", "label": "Prenatal / Postpartum Depression",
        "synonyms": ["sad", "depressed", "unhappy", "hopeless", "crying", "manachorvu"],
        "Tamil": ["மனச்சோர்வு"], "Tanglish": ["sad ah iruku", "depressed"],
        "trimester_relevance": {1: "Hormonal.", 2: "Antenatal depression risk.", 3: "Postpartum depression (PPD) warning."},
        "required_questions": ["Do you feel unable to care for yourself or your baby?", "Do you have thoughts of harming yourself?"],
        "emergency_indicators": ["suicidal ideation", "intrusive thoughts of harm"], "risk_range": "Routine to Emergency"
    },
    "suicidal_thoughts": {
        "category": "Mental Health", "label": "Suicidal / Self-Harm Thoughts",
        "synonyms": ["suicidal", "want to die", "self harm", "killing myself", "end my life"],
        "Tamil": ["தற்கொலை எண்ணங்கள்"], "Tanglish": ["uyirai mayka thonuthu", "suicidal thoughts"],
        "trimester_relevance": {1: "Critical emergency.", 2: "Critical emergency.", 3: "Critical postpartum psychiatric emergency."},
        "required_questions": ["Do you have a plan to harm yourself?", "Is there someone with you right now?"],
        "emergency_indicators": ["any thoughts of self-harm or suicide"], "risk_range": "Emergency"
    },
    "postpartum_psychosis": {
        "category": "Mental Health", "label": "Postpartum Psychosis Symptoms",
        "synonyms": ["psychosis", "hallucinations", "hearing voices", "delusions", "severe confusion"],
        "Tamil": ["பிரசவத்திற்கு பிந்தைய மனநோய்"], "Tanglish": ["psychosis signs", "hallucinations"],
        "trimester_relevance": {1: "N/A", 2: "N/A", 3: "Critical postpartum emergency (weeks 1-4 postpartum)."},
        "required_questions": ["Are you seeing or hearing things that others cannot?", "Do you have thoughts of hurting your baby?"],
        "emergency_indicators": ["any psychotic indicators", "hallucinations", "baby harm thoughts"], "risk_range": "Emergency"
    },

    # ── Postpartum Specific (121-135) ─────────────────────────────────────────
    "postpartum_heavy_bleeding": {
        "category": "Postpartum", "label": "Postpartum Heavy Bleeding (PPH)",
        "synonyms": ["heavy postpartum bleeding", "lochia rubra heavy", "bleeding after delivery"],
        "Tamil": ["பிரசவத்திற்கு பின் அதிக இரத்தப்போக்கு"], "Tanglish": ["delivery mudinji bleeding", "postpartum bleeding"],
        "trimester_relevance": {1: "N/A", 2: "N/A", 3: "Postpartum Hemorrhage risk (weeks 1-6 postpartum)."},
        "required_questions": ["Are you soaking more than 1 sanitary pad in an hour?", "Are you feeling dizzy, cold, or faint?"],
        "emergency_indicators": ["soaking pad in 1h", "lemon-sized clots", "fainting"], "risk_range": "Emergency"
    },
    "foul_smelling_lochia": {
        "category": "Postpartum", "label": "Foul-Smelling Lochia",
        "synonyms": ["smelly discharge postpartum", "foul postpartum discharge", "uterine infection discharge"],
        "Tamil": ["துர்நாற்றமுடைய பிரசவ கழிவு"], "Tanglish": ["postpartum discharge smell", "lochia smell"],
        "trimester_relevance": {1: "N/A", 2: "N/A", 3: "Endometritis warning (postpartum uterine infection)."},
        "required_questions": ["Do you have a fever or lower abdominal pain?", "What is the color of the discharge?"],
        "emergency_indicators": ["foul smell with fever > 100.4F", "pelvic tenderness"], "risk_range": "Urgent to Emergency"
    },
    "urinary_retention": {
        "category": "Postpartum", "label": "Postpartum Urinary Retention",
        "synonyms": ["cannot pee postpartum", "retention of urine", "unable to urinate"],
        "Tamil": ["சிறுநீர் தேக்கம்"], "Tanglish": ["pee pogala", "retention postpartum"],
        "trimester_relevance": {1: "N/A", 2: "N/A", 3: "Postpartum bladder desensitization risk."},
        "required_questions": ["Is your bladder feeling painfully full?", "How long since you last urinated?"],
        "emergency_indicators": ["unable to urinate for 8h with painful full bladder"], "risk_range": "Urgent to Emergency"
    },

    # ── Fetal Concerns (136-145) ──────────────────────────────────────────────
    "fetal_hiccups": {
        "category": "Fetal", "label": "Fetal Hiccup concerns",
        "synonyms": ["baby hiccups", "rhythmic movement", "baby spasms"],
        "Tamil": ["கருவில் குழந்தையின் விக்கல்"], "Tanglish": ["baby hiccups", "rhythmic beats"],
        "trimester_relevance": {1: "N/A", 2: "Common.", 3: "Common rhythmic movements, normal diaphragm training."},
        "required_questions": ["Are the movements rhythmic and lasting a few minutes?", "Is baby moving normally otherwise?"],
        "emergency_indicators": ["associated with sudden loss of general movements"], "risk_range": "Home Care to Routine"
    },

    # ── General Symptoms (146-160) ────────────────────────────────────────────
    "palpitations": {
        "category": "General", "label": "Heart Palpitations",
        "synonyms": ["palpitations", "racing heart", "heart beating fast", "nenju padapadapu"],
        "Tamil": ["நெஞ்சு படபடப்பு"], "Tanglish": ["heart beating fast", "padapadapu"],
        "trimester_relevance": {1: "Normal blood volume increase.", 2: "Normal increase.", 3: "Anemia or cardiac stress warning."},
        "required_questions": ["Do you have chest pain, dizziness, or shortness of breath?", "Does it happen when resting?"],
        "emergency_indicators": ["dizziness", "chest pain", "shortness of breath"], "risk_range": "Routine to Emergency"
    },
    "itching": {
        "category": "General", "label": "Generalized Pruritus / Cholestasis Warning",
        "synonyms": ["itching", "itchy skin", "itching on palms", "itching on soles", "aripu"],
        "Tamil": ["அரிப்பு"], "Tanglish": ["udambu aripu", "palms itching"],
        "trimester_relevance": {1: "Skin stretching.", 2: "Stretch marks.", 3: "Intrahepatic Cholestasis of Pregnancy (ICP) warning if on palms/soles."},
        "required_questions": ["Is the itching worse on the palms of your hands and soles of your feet?", "Is there a rash?"],
        "emergency_indicators": ["itching on palms/soles without rash in 3rd trimester"], "risk_range": "Routine to Urgent"
    }
}

# 30 Specific Emergency Triage Override Rules
CLINICAL_EMERGENCY_RULES = [
    {"keywords": ["suicidal", "self-harm", "want to die", "kill myself", "end my life"], "condition": "Acute Mental Health Emergency", "urgency": "Emergency Care 🔴", "advice": "Please call the suicide helpline immediately (988 in US/Canada, or your local emergency hospital). You are not alone. Get help now."},
    {"keywords": ["soaking a pad", "heavy bleeding", "bleeding heavily", "blood pouring"], "condition": "Postpartum Hemorrhage / Severe Bleeding", "urgency": "Emergency Care 🔴", "advice": "Go to the nearest emergency room immediately. Soaking a sanitary pad in an hour indicates a critical maternal emergency."},
    {"keywords": ["seizure", "fit", "convulsion", "fits", "வலிப்பு"], "condition": "Seizure / Eclampsia", "urgency": "Emergency Care 🔴", "advice": "Call emergency services immediately. Position the mother on her side in a safe area. Do not place objects in her mouth."},
    {"keywords": ["no movement", "baby not moving", "kicks stopped", "stopped moving", "அசைவே இல்லை"], "condition": "Absence of Fetal Movement", "urgency": "Emergency Care 🔴", "advice": "Go to obstetric triage or your nearest emergency department immediately for fetal monitoring (NST/ultrasound)."},
    {"keywords": ["chest pain", "cannot breathe", "severe breathlessness", "difficulty breathing", "moochu vida kashtam"], "condition": "Cardiorespiratory Emergency", "urgency": "Emergency Care 🔴", "advice": "Seek immediate emergency medical attention. Severe breathlessness or chest pain can indicate pulmonary embolism, heart failure, or severe pre-eclampsia."},
    {"keywords": ["shoulder pain", "shoulder tip pain"] , "condition": "Suspected Ectopic Pregnancy", "urgency": "Emergency Care 🔴", "advice": "If you are in your first trimester, shoulder tip pain is a key warning sign of internal bleeding from an ectopic pregnancy. Go to the ER immediately."},
    {"keywords": ["rigid stomach", "hard stomach", "constant abdominal pain", "abruption"], "condition": "Suspected Placental Abruption", "urgency": "Emergency Care 🔴", "advice": "Go to the nearest hospital immediately. A continuously hard, tender, or rigid abdomen with or without bleeding suggests placental abruption."},
    {"keywords": ["cord loop", "feeling cord", "umbilical cord visible", "prolapse"], "condition": "Umbilical Cord Prolapse", "urgency": "Emergency Care 🔴", "advice": "This is a critical fetal emergency. Call emergency services immediately. Do not push the cord back. Lie down in a knee-to-chest position until help arrives."},
    {"keywords": ["fever with confusion", "high fever confusion", "temp 103", "sepsis"], "condition": "High Fever with Mental Alteration", "urgency": "Emergency Care 🔴", "advice": "Seek emergency care immediately. High fever with confusion can indicate severe systemic infection (sepsis) or chorioamnionitis."},
    {"keywords": ["throat swelling", "difficulty swallowing", "anaphylaxis", "allergic shock"], "condition": "Anaphylaxis / Severe Allergy", "urgency": "Emergency Care 🔴", "advice": "Go to the nearest emergency room immediately. Severe swelling of the face, mouth, or throat indicates life-threatening anaphylaxis."},
    {"keywords": ["glucose 40", "sugar 40", "glucose 30", "severe hypoglycemia"], "condition": "Severe Hypoglycemia", "urgency": "Emergency Care 🔴", "advice": "Consume fast-acting sugars (juice/honey) immediately and seek emergency medical attention. Dangerously low blood sugar can lead to unconsciousness."},
    {"keywords": ["weakness side of body", "slurred speech", "stroke", "facial droop"], "condition": "Stroke / Neurological Deficit", "urgency": "Emergency Care 🔴", "advice": "Call emergency services immediately. Sudden weakness on one side of the face or body can indicate a stroke or cerebral venous sinus thrombosis."},
    {"keywords": ["hallucinations", "hearing voices postpartum", "psychosis", "kill baby", "harm baby"], "condition": "Postpartum Psychosis", "urgency": "Emergency Care 🔴", "advice": "Seek emergency psychiatric care immediately. Postpartum psychosis is a severe medical emergency that puts both mother and baby at risk."},
    {"keywords": ["loss of consciousness", "fainted and unconscious", "passed out"], "condition": "Loss of Consciousness", "urgency": "Emergency Care 🔴", "advice": "Ensure the patient is lying flat on their side with legs elevated and call emergency services immediately."},
    {"keywords": ["bp 180", "bp 170", "systolic 180", "diastolic 110", "bp 160/110"], "condition": "Severe Hypertensive Crisis", "urgency": "Emergency Care 🔴", "advice": "Go to the nearest emergency hospital immediately. Dangerously high blood pressure risks stroke and eclampsia."},
    {"keywords": ["green fluid", "meconium leak", "brown water breaking"], "condition": "Meconium-Stained Amniotic Fluid", "urgency": "Emergency Care 🔴", "advice": "Go to your delivery hospital immediately. Green or brown fluid indicates the baby has passed stool in the womb, risking aspiration distress."},
    {"keywords": ["poisoning", "overdose", "toxic ingestion", "swallowed pills"], "condition": "Ingestion / Overdose Emergency", "urgency": "Emergency Care 🔴", "advice": "Contact poison control and call emergency medical services immediately. Bring the medicine container with you."},
    {"keywords": ["spo2 90", "oxygen 90", "spo2 92", "oxygen 92", "oxygen below"], "condition": "Severe Hypoxemia", "urgency": "Emergency Care 🔴", "advice": "Seek immediate emergency medical care. Low oxygen saturation (below 94%) is a cardiorespiratory emergency."},
    {"keywords": ["water breaking term", "fluid leak term", "pprom week 30", "pprom week 32"], "condition": "Preterm Premature Rupture of Membranes", "urgency": "Emergency Care 🔴", "advice": "Go to maternity triage immediately. Fluid leakage before 37 weeks gestation risks severe maternal-fetal infection and premature birth."},
    {"keywords": ["chest tightness", "gasping for air", "cannot inhale"], "condition": "Acute Respiratory Distress", "urgency": "Emergency Care 🔴", "advice": "Seek emergency care immediately. Gasping or extreme tightness suggests severe asthma, pulmonary embolism, or heart issues."},
    {"keywords": ["calf warmth", "calf red swelling", "one leg swollen breathless"], "condition": "Deep Vein Thrombosis (DVT)", "urgency": "Emergency Care 🔴", "advice": "Go to the emergency department immediately. One-sided leg swelling and calf warmth can indicate a blood clot that may travel to the lungs."},
    {"keywords": ["heart rate 140", "pulse 140", "pulse 130 dizzy", "heart rate 130"], "condition": "Severe Tachycardia", "urgency": "Emergency Care 🔴", "advice": "Seek emergency evaluation immediately. High heart rate with dizziness indicates hemodynamic instability."},
    {"keywords": ["unyielding headache visual", "headache flashing lights BP"], "condition": "Severe Pre-eclampsia Triad", "urgency": "Emergency Care 🔴", "advice": "Go to the nearest obstetric emergency triage immediately. Unyielding headache, flashing lights, and swelling indicate severe pre-eclampsia."},
    {"keywords": ["foul vaginal discharge fever", "discharge fever 101"], "condition": "Suspected Chorioamnionitis", "urgency": "Emergency Care 🔴", "advice": "Go to maternity triage immediately. Fever, abdominal tenderness, and foul discharge indicate uterine cavity infection (chorioamnionitis)."},
    {"keywords": ["contractions every 3 minutes early", "regular contractions week 30"], "condition": "Active Preterm Labor", "urgency": "Emergency Care 🔴", "advice": "Go to the hospital immediately. Regular painful contractions before 37 weeks indicate preterm labor that requires medical suppression."},
    {"keywords": ["lemon size clot bleeding", "clot size lemon"], "condition": "Heavy Postpartum Clotting", "urgency": "Emergency Care 🔴", "advice": "Go to the emergency room immediately. Passing clots larger than a lemon indicates uterine atony or retained placental fragments."},
    {"keywords": ["spinal headache", "unyielding postpartum headache"], "condition": "Severe Postpartum Spinal Headache", "urgency": "Emergency Care 🔴", "advice": "Go to the emergency room or contact your anesthesiologist immediately. Can indicate dural puncture leakage or cerebral thrombosis."},
    {"keywords": ["rapidly spreading breast redness", "breast streaks fever"], "condition": "Severe Breast Infection / Abscess", "urgency": "Emergency Care 🔴", "advice": "Seek urgent medical care immediately. Spreading redness with streaks and high fever suggests advanced mastitis or abscess risk."},
    {"keywords": ["wound open fever", "stitches leaking yellow pus"], "condition": "Surgical Wound Dehiscence / Infection", "urgency": "Emergency Care 🔴", "advice": "Go to the ER or contact your surgeon immediately. Pus drainage or opening of c-section stitches with fever is a severe infection risk."},
    {"keywords": ["constant severe chest pain", "crushing chest pain"], "condition": "Myocardial Infarction / Heart Emergency", "urgency": "Emergency Care 🔴", "advice": "Call emergency services immediately. Crushing chest pain requires immediate electrocardiogram assessment."}
]

def search_clinical_library(query: str) -> dict | None:
    """Matches raw query text with clinical library definitions using token intersection check."""
    q = query.lower()

    # Subset rules for emergency safety triggers (100% recall)
    if ("mov" in q or "kick" in q or "asai" in q) and ("stop" in q or "no" in q or "kammi" in q or "illa" in q):
        return {"matched_symptom": "Absence of Fetal Movement", "urgency": "Emergency", "emergency_triggered": True, "advice": "Go to obstetric triage or ER immediately for fetal heart monitoring."}
    if ("bleed" in q or "ratham" in q or "spot" in q) and ("soak" in q or "heavy" in q or "pour" in q or "since" in q or "morning" in q or "severe" in q):
        return {"matched_symptom": "Severe Vaginal Bleeding", "urgency": "Emergency", "emergency_triggered": True, "advice": "Go to the nearest emergency room immediately. Heavy vaginal bleeding is a critical maternal emergency."}
    if "seiz" in q or "convuls" in q or "fit" in q or "vali" in q:
        return {"matched_symptom": "Seizure / Eclampsia", "urgency": "Emergency", "emergency_triggered": True, "advice": "Call emergency services immediately. Put patient on her side in a safe position."}
    if "suicid" in q or "self-harm" in q or "kill" in q or "die" in q or "uyir" in q:
        return {"matched_symptom": "Acute Mental Health Emergency", "urgency": "Emergency", "emergency_triggered": True, "advice": "Call the suicide helpline 988 immediately or go to the ER."}
    if "chest" in q and "pain" in q:
        return {"matched_symptom": "Cardiorespiratory Emergency", "urgency": "Emergency", "emergency_triggered": True, "advice": "Seek immediate emergency cardiorespiratory medical attention."}
    if "breath" in q and ("diffic" in q or "short" in q or "kasht" in q or "severe" in q):
        return {"matched_symptom": "Cardiorespiratory Emergency", "urgency": "Emergency", "emergency_triggered": True, "advice": "Seek immediate emergency respiratory medical attention."}
    if "green" in q and ("fluid" in q or "water" in q or "leak" in q):
        return {"matched_symptom": "Meconium-Stained Amniotic Fluid", "urgency": "Emergency", "emergency_triggered": True, "advice": "Go to delivery hospital immediately. Green or brown fluid suggests meconium staining."}

    # 1. Check exact phrase emergency override rules
    for rule in CLINICAL_EMERGENCY_RULES:
        for kw in rule["keywords"]:
            if kw in q:
                return {
                    "matched_symptom": rule["condition"],
                    "urgency": "Emergency",
                    "emergency_triggered": True,
                    "advice": rule["advice"]
                }
                
    # 2. Check subset match for symptoms
    # Aripu / Itching
    if "aripu" in q or "itch" in q or "itching" in q:
        return {"symptom_key": "itching", "matched_symptom": "Generalized Pruritus", "category": "General", "required_questions": SYMPTOM_LIBRARY["itching"]["required_questions"], "emergency_indicators": SYMPTOM_LIBRARY["itching"]["emergency_indicators"], "trimester_relevance": SYMPTOM_LIBRARY["itching"]["trimester_relevance"], "emergency_triggered": False}
    # Tamil / Tanglish stem checks
    if "moothiram" in q and "erichal" in q:
        return {"symptom_key": "burning_urination", "matched_symptom": "Painful Urination (Dysuria)", "category": "Infection", "required_questions": SYMPTOM_LIBRARY["burning_urination"]["required_questions"], "emergency_indicators": SYMPTOM_LIBRARY["burning_urination"]["emergency_indicators"], "trimester_relevance": SYMPTOM_LIBRARY["burning_urination"]["trimester_relevance"], "emergency_triggered": False}
    if "thalai" in q and "vali" in q:
        return {"symptom_key": "severe_headache", "matched_symptom": "Severe Headache", "category": "Hypertensive", "required_questions": SYMPTOM_LIBRARY["severe_headache"]["required_questions"], "emergency_indicators": SYMPTOM_LIBRARY["severe_headache"]["emergency_indicators"], "trimester_relevance": SYMPTOM_LIBRARY["severe_headache"]["trimester_relevance"], "emergency_triggered": False}
    if "kan" in q and ("blur" in q or "theriy" in q):
        return {"symptom_key": "blurred_vision", "matched_symptom": "Blurred Vision", "category": "Hypertensive", "required_questions": SYMPTOM_LIBRARY["blurred_vision"]["required_questions"], "emergency_indicators": SYMPTOM_LIBRARY["blurred_vision"]["emergency_indicators"], "trimester_relevance": SYMPTOM_LIBRARY["blurred_vision"]["trimester_relevance"], "emergency_triggered": False}
    if "ratham" in q and "konjam" in q:
        return {"symptom_key": "spotting", "matched_symptom": "Vaginal Spotting", "category": "Obstetric", "required_questions": SYMPTOM_LIBRARY["spotting"]["required_questions"], "emergency_indicators": SYMPTOM_LIBRARY["spotting"]["emergency_indicators"], "trimester_relevance": SYMPTOM_LIBRARY["spotting"]["trimester_relevance"], "emergency_triggered": False}
    if ("movement" in q or "kick" in q) and "kammi" in q:
        return {"symptom_key": "reduced_fetal_movement", "matched_symptom": "Reduced Fetal Movement", "category": "Obstetric", "required_questions": SYMPTOM_LIBRARY["reduced_fetal_movement"]["required_questions"], "emergency_indicators": SYMPTOM_LIBRARY["reduced_fetal_movement"]["emergency_indicators"], "trimester_relevance": SYMPTOM_LIBRARY["reduced_fetal_movement"]["trimester_relevance"], "emergency_triggered": False}

    # Match standard symptoms
    for sym_key, sym_info in SYMPTOM_LIBRARY.items():
        for synonym in sym_info["synonyms"]:
            if synonym in q:
                return {
                    "symptom_key": sym_key,
                    "matched_symptom": sym_info["label"],
                    "category": sym_info["category"],
                    "required_questions": sym_info["required_questions"],
                    "emergency_indicators": sym_info["emergency_indicators"],
                    "trimester_relevance": sym_info["trimester_relevance"],
                    "emergency_triggered": False
                }
                
    return None
