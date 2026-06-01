"""P1 ScenarioPlanner — specialty-aligned briefs (prompt-faithful)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.case_generator import config


@dataclass(frozen=True)
class ClinicalVariant:
    diagnosis: str
    treatment_requested: str
    clinical_facts: str  # specific meds, dates, scores for P3
    rebuttal_core: str


def _age_in_band(band: str, index: int) -> int:
    spans = {
        "18-25": (19, 25),
        "26-40": (27, 40),
        "41-55": (42, 55),
        "56-70": (57, 69),
        "71+": (72, 78),
    }
    lo, hi = spans.get(band, (30, 50))
    return lo + ((index * 7) % (hi - lo + 1))


# ≥12 variants per specialty; index selects variant within specialty.
SPECIALTY_VARIANTS: dict[str, list[ClinicalVariant]] = {
    "behavioral_health": [
        ClinicalVariant(
            "Major depressive disorder, recurrent, moderate (F33.1)",
            "Intensive outpatient program (IOP) for depression",
            "PHQ-9 scores 19 and 21 in Q4 2025 and Q1 2026; failed sertraline 200 mg ×14 weeks and bupropion XL 300 mg ×12 weeks.",
            "IOP is indicated after two adequate antidepressant trials with persistent functional impairment.",
        ),
        ClinicalVariant(
            "Generalized anxiety disorder (F41.1)",
            "Additional psychotherapy visits beyond plan annual limit",
            "GAD-7 remained 16 after 16 sessions; prior auth supported weekly therapy for acute worsening in March 2026.",
            "Visit-cap denials ignore MHPAEA parity when medical/surgical follow-ups are not similarly capped.",
        ),
        ClinicalVariant(
            "Severe obsessive-compulsive disorder (F42.2)",
            "Transcranial magnetic stimulation (TMS)",
            "Y-BOCS 29 after fluvoxamine 300 mg ×16 weeks and clomipramine 200 mg ×14 weeks plus ERP since 2024.",
            "TMS meets CPB criteria when two medication classes and ERP have failed with documented scores.",
        ),
        ClinicalVariant(
            "Bipolar II disorder, current depressed episode (F31.81)",
            "Partial hospitalization program (PHP)",
            "Quetiapine and lamotrigine trials with PHP referral after emergency department visit for severe functional decline.",
            "PHP is appropriate when outpatient care cannot stabilize mood symptoms.",
        ),
        ClinicalVariant(
            "Attention-deficit/hyperactivity disorder, combined (F90.2)",
            "Adult ADHD coaching plus medication management extension",
            "Documented workplace impairment; atomoxetine 80 mg daily trialed 10 weeks with partial response.",
            "Coaching paired with pharmacotherapy is standard when impairment persists.",
        ),
        ClinicalVariant(
            "Post-traumatic stress disorder, chronic (F43.12)",
            "Prolonged exposure therapy beyond visit cap",
            "CAPS-5 score 42; completed 12 sessions with minimal symptom change.",
            "Trauma-focused therapy requires sufficient visits to complete exposure hierarchy.",
        ),
        ClinicalVariant(
            "Alcohol use disorder, severe (F10.20)",
            "Inpatient medical detoxification (3–5 days)",
            "CIWA-Ar peaked at 17 with tremor and tachycardia; outpatient detox deemed unsafe by ED physician.",
            "Inpatient detox is medically necessary when withdrawal risk is moderate-severe.",
        ),
        ClinicalVariant(
            "Binge-eating disorder (F50.81)",
            "Adjunct lisdexamfetamine for BED",
            "Failed topiramate 100 mg and structured behavioral program 20 weeks; BMI 36 with metabolic syndrome.",
            "Pharmacotherapy is guideline-supported after behavioral intervention failure.",
        ),
        ClinicalVariant(
            "Persistent depressive disorder (F34.1)",
            "Spravato (esketamine) nasal therapy",
            "Failed venlafaxine XR 225 mg and mirtazapine 30 mg; PHQ-9 ≥18 for nine months.",
            "Esketamine is indicated for treatment-resistant depression with documented trials.",
        ),
        ClinicalVariant(
            "Social anxiety disorder, severe (F40.10)",
            "Group cognitive behavioral therapy (16 sessions)",
            "Failed sertraline and escitalopram trials; avoids work due to panic symptoms in meetings.",
            "Structured CBT is first-line when pharmacotherapy insufficient.",
        ),
        ClinicalVariant(
            "Panic disorder with agoraphobia (F40.01)",
            "Psychiatric partial hospitalization",
            "Multiple ER visits in 2025; lorazepam taper completed; SSRIs partially effective only.",
            "Higher level of care warranted with recurrent ER utilization.",
        ),
        ClinicalVariant(
            "Insomnia disorder, chronic (G47.00)",
            "Cognitive behavioral therapy for insomnia (CBT-I), 8 sessions",
            "Sleep diary shows 4.2 hours/night average; failed zolpidem 10 mg with next-day impairment.",
            "CBT-I is preferred over chronic hypnotic use.",
        ),
    ],
    "cardiology": [
        ClinicalVariant(
            "Paroxysmal atrial fibrillation (I48.0)",
            "Catheter ablation for symptomatic AFib",
            "Failed dofetilide and sotalol with Holter-documented burden 18%; CHA2DS2-VASc 2.",
            "Ablation appropriate after antiarrhythmic failure with symptomatic burden.",
        ),
        ClinicalVariant(
            "Heart failure with reduced ejection fraction (I50.20)",
            "Cardiac resynchronization therapy (CRT-D)",
            "LVEF 28% on optimal GDMT; LBBB QRS 152 ms despite sacubitril/valsartan and carvedilol.",
            "CRT indicated with EF ≤35% and wide QRS despite medical therapy.",
        ),
        ClinicalVariant(
            "Refractory hypertension (I10)",
            "Renal denervation referral",
            "BP 168/104 on amlodipine, chlorthalidone, and losartan at maximized doses.",
            "Resistant hypertension defined after three agents including diuretic.",
        ),
        ClinicalVariant(
            "Stable angina with positive stress test (I20.9)",
            "Coronary CT angiography",
            "Typical angina class II; stress ECG with 2 mm ST depression at 7 METs.",
            "Non-invasive imaging warranted with intermediate pre-test probability.",
        ),
        ClinicalVariant(
            "Familial hypercholesterolemia (E78.01)",
            "PCSK9 inhibitor (evolocumab)",
            "LDL 196 mg/dL on high-intensity statin plus ezetimibe; ASCVD risk elevated.",
            "PCSK9 therapy indicated when LDL remains above goal on maximally tolerated statin.",
        ),
        ClinicalVariant(
            "Symptomatic aortic stenosis, moderate (I35.0)",
            "Transcatheter aortic valve replacement (TAVR) evaluation",
            "Syncope episode 2025; valve area 1.0 cm² with mean gradient 38 mmHg.",
            "TAVR evaluation appropriate with symptoms and hemodynamically significant AS.",
        ),
        ClinicalVariant(
            "Recurrent vasovagal syncope (R55)",
            "Implantable loop recorder",
            "Three syncope events in 12 months; orthostatics and echo unrevealing.",
            "ILR indicated for recurrent unexplained syncope.",
        ),
        ClinicalVariant(
            "Long QT syndrome type 2 (I49.5)",
            "Genetic cardiology consult and beta-blocker titration",
            "QTc 498 ms on ECG; family history of sudden death.",
            "Specialist management required for inherited arrhythmia syndrome.",
        ),
        ClinicalVariant(
            "Pulmonary arterial hypertension, suspected (I27.0)",
            "Right heart catheterization",
            "Echo RVSP 48 mmHg with progressive dyspnea on exertion.",
            "Catheterization required to confirm PAH and guide therapy.",
        ),
        ClinicalVariant(
            "Post-MI ventricular tachycardia (I25.2)",
            "Subcutaneous ICD",
            "Sustained VT episode 2025; EF 35% after anterior MI.",
            "ICD indicated for secondary prevention after sustained VT.",
        ),
        ClinicalVariant(
            "Hypertrophic cardiomyopathy (I42.2)",
            "Septal myectomy evaluation",
            "LVOT gradient 65 mmHg on stress echo with NYHA class III symptoms.",
            "Surgical myectomy considered when gradient and symptoms persist on medical therapy.",
        ),
        ClinicalVariant(
            "Wolff-Parkinson-White pattern with SVT (I45.6)",
            "Electrophysiology study with ablation",
            "Monthly palpitation episodes; delta wave on resting ECG.",
            "EP study standard when symptomatic WPW present.",
        ),
    ],
    "endocrine": [
        ClinicalVariant(
            "Type 2 diabetes mellitus with labile glucose (E11.65)",
            "Continuous glucose monitor (Dexcom G7)",
            "Basal-bolus regimen with nocturnal hypoglycemia to 48 mg/dL on fingersticks.",
            "CGM indicated with hypoglycemia unawareness on multi-dose insulin.",
        ),
        ClinicalVariant(
            "Hypothyroidism, inadequately controlled (E03.9)",
            "Liothyronine (T3) adjunct therapy",
            "TSH 6.8 mIU/L on levothyroxine 150 mcg; persistent fatigue and weight gain.",
            "Adjunct therapy considered when symptoms persist despite levothyroxine.",
        ),
        ClinicalVariant(
            "Polycystic ovary syndrome with hyperandrogenism (E28.2)",
            "Spironolactone for androgenic symptoms",
            "Failed OCP trial due to migraine aura; hirsutism score elevated.",
            "Anti-androgen therapy supported when OCP contraindicated.",
        ),
        ClinicalVariant(
            "Primary hyperparathyroidism (E21.0)",
            "Parathyroidectomy",
            "Calcium 11.4 mg/dL, PTH 128 pg/mL, kidney stones in 2024.",
            "Surgery indicated with symptomatic hypercalcemia or stones.",
        ),
        ClinicalVariant(
            "Cushing disease, suspected (E24.0)",
            "Pituitary MRI with endocrinology referral",
            "DEXA T-score -2.4, striae, glucose intolerance, elevated 24h urine cortisol.",
            "Workup warranted with biochemical hypercortisolism.",
        ),
        ClinicalVariant(
            "Type 1 diabetes mellitus (E10.9)",
            "Insulin pump upgrade (automated delivery)",
            "HbA1c 8.9% despite MDI; severe dawn phenomenon.",
            "Pump therapy appropriate when MDI fails glycemic targets.",
        ),
        ClinicalVariant(
            "Osteoporosis, postmenopausal (M81.0)",
            "Teriparatide anabolic therapy",
            "Fragility fracture 2025; failed alendronate 18 months.",
            "Anabolic agent indicated after bisphosphonate failure with fracture.",
        ),
        ClinicalVariant(
            "Adrenal insufficiency, primary (E27.1)",
            "Hydrocortisone stress-dose education plus ACTH stim retest",
            "Morning cortisol 2.1 mcg/dL; hyperpigmentation present.",
            "Replacement and diagnostic confirmation required.",
        ),
        ClinicalVariant(
            "Graves disease with ophthalmopathy (E05.00)",
            "Teprotumumab for thyroid eye disease",
            "CAS score 5/7 with diplopia; euthyroid on methimazole.",
            "Teprotumumab FDA-approved for active moderate-to-severe TED.",
        ),
        ClinicalVariant(
            "Male hypogonadism (E29.1)",
            "Testosterone cypionate with monitoring",
            "AM testosterone 198 ng/dL ×2; fatigue and low libido.",
            "Replacement when symptomatic with confirmed low morning levels.",
        ),
        ClinicalVariant(
            "Diabetic gastroparesis (K31.84)",
            "Gastric electrical stimulation evaluation",
            "Gastric emptying study 180 min retention; recurrent vomiting on metoclopramide.",
            "Device therapy considered for refractory gastroparesis.",
        ),
        ClinicalVariant(
            "Obesity with BMI 42 and prediabetes (E66.01)",
            "GLP-1 receptor agonist (semaglutide 2.4 mg)",
            "BMI 42; HbA1c 6.2%; failed structured lifestyle program 6 months.",
            "Pharmacotherapy indicated per obesity guidelines after lifestyle trial.",
        ),
    ],
    "msk": [
        ClinicalVariant(
            "Lumbar radiculopathy with neurogenic claudication (M54.16)",
            "L4-L5 microdiscectomy",
            "18 PT sessions over 14 weeks; MRI central disc herniation contacting traversing nerve root.",
            "Surgery appropriate after failed conservative care with correlating imaging.",
        ),
        ClinicalVariant(
            "Rotator cuff tear, full-thickness (M75.101)",
            "Arthroscopic rotator cuff repair",
            "Failed 14 weeks PT; MRI supraspinatus full-thickness tear 1.8 cm.",
            "Repair indicated with persistent weakness and full-thickness tear.",
        ),
        ClinicalVariant(
            "Knee osteoarthritis, severe medial compartment (M17.11)",
            "Unicompartmental knee arthroplasty",
            "BMI 27; failed NSAIDs, injections ×3, and 12 weeks PT; varus alignment.",
            "UKA for unicompartmental disease after conservative failure.",
        ),
        ClinicalVariant(
            "Cervical spondylosis with radiculopathy (M47.22)",
            "Anterior cervical discectomy and fusion C5-6",
            "Arm weakness 4/5; EMG active radiculopathy; 8 weeks PT failed.",
            "Fusion when myelopathy/radiculopathy correlates with level.",
        ),
        ClinicalVariant(
            "Plantar fasciitis, chronic (M72.2)",
            "Extracorporeal shock wave therapy",
            "6 months stretching, night splint, and podiatry care without relief.",
            "ESWT considered after prolonged conservative therapy.",
        ),
        ClinicalVariant(
            "Hip labral tear (M24.151)",
            "Hip arthroscopy with labral repair",
            "Positive anterior impingement tests; MRI labral tear with paralabral cyst.",
            "Arthroscopy for symptomatic labral pathology.",
        ),
        ClinicalVariant(
            "Compression fracture T12, osteoporotic (M80.08XA)",
            "Kyphoplasty",
            "Pain 8/10 limiting ambulation; MRI acute fracture; failed brace 3 weeks.",
            "Vertebral augmentation for painful acute osteoporotic fracture.",
        ),
        ClinicalVariant(
            "Carpal tunnel syndrome, severe (G56.00)",
            "Carpal tunnel release",
            "EMG severe median neuropathy; thenar atrophy noted.",
            "Release indicated with severe electrodiagnostic findings.",
        ),
        ClinicalVariant(
            "Achilles tendinopathy, chronic (M76.60)",
            "Platelet-rich plasma injection",
            "Eccentric loading 16 weeks; ultrasound tendinosis with neovascularity.",
            "PRP sometimes covered after failed rehabilitation.",
        ),
        ClinicalVariant(
            "Frozen shoulder (M75.00)",
            "Manipulation under anesthesia",
            "ROM flexion 90° after 5 months PT and intra-articular steroid.",
            "MUA for adhesive capsulitis refractory to therapy.",
        ),
        ClinicalVariant(
            "Ankle instability, chronic lateral (M25.371)",
            "Broström ligament repair",
            "Repeated inversion injuries; MRI ATFL attenuation.",
            "Surgical stabilization after failed bracing and PT.",
        ),
        ClinicalVariant(
            "Degenerative meniscal tear, medial (M23.205)",
            "Partial meniscectomy",
            "Mechanical locking symptoms; MRI horizontal tear not improving with PT.",
            "Arthroscopy for mechanical symptoms with correlating tear.",
        ),
    ],
    "oncology": [
        ClinicalVariant(
            "HR-positive, HER2-negative early breast cancer (C50.911)",
            "Adjuvant abemaciclib with endocrine therapy",
            "Stage IIB, Ki-67 32%, four positive nodes on sentinel biopsy.",
            "CDK4/6 inhibitor supported in high-risk early breast cancer per NCCN.",
        ),
        ClinicalVariant(
            "Stage III colon adenocarcinoma (C18.9)",
            "Adjuvant FOLFOX chemotherapy",
            "Post-colectomy pathology T3N1; ECOG 0.",
            "Adjuvant chemo standard for node-positive colon cancer.",
        ),
        ClinicalVariant(
            "Diffuse large B-cell lymphoma (C83.30)",
            "R-CHOP cycle continuation",
            "PET interim Deauville 4; cycle 3 completed without dose-limiting toxicity.",
            "Completion of curative-intent chemoimmunotherapy.",
        ),
        ClinicalVariant(
            "Metastatic castration-sensitive prostate cancer (C61)",
            "Apalutamide plus androgen deprivation therapy",
            "Rising PSA 18 ng/mL on ADT alone; bone scan negative.",
            "Intensification standard for high-risk biochemical recurrence pattern.",
        ),
        ClinicalVariant(
            "Ovarian cancer, platinum-sensitive recurrence (C56.9)",
            "Secondary cytoreductive surgery evaluation",
            "CA-125 rise from 22 to 210 U/mL; CT localized pelvic recurrence.",
            "Surgery considered for isolated platinum-sensitive relapse.",
        ),
        ClinicalVariant(
            "Non-small cell lung cancer, stage IV EGFR+ (C34.90)",
            "Osimertinib third-line after T790M-negative progression",
            "Progression on erlotinib and carboplatin/pemetrexed; liquid biopsy pending.",
            "Targeted therapy sequencing per molecular profile.",
        ),
        ClinicalVariant(
            "Melanoma stage IIIB (C43.9)",
            "Adjuvant pembrolizumab",
            "BRAF wild-type; SLNB positive; wide excision completed.",
            "Adjuvant anti-PD-1 standard for stage III melanoma.",
        ),
        ClinicalVariant(
            "Multiple myeloma, relapsed (C90.00)",
            "Carfilzomib-based triplet",
            "Progressive M-spike after lenalidomide maintenance; creatinine stable.",
            "Salvage proteasome inhibitor regimen at relapse.",
        ),
        ClinicalVariant(
            "Chronic lymphocytic leukemia, symptomatic (C91.10)",
            "Venetoclax plus obinutuzumab",
            "WBC 85k, hemoglobin 10.2 g/dL, bulky nodes; Binet stage C symptoms.",
            "Systemic therapy indicated with symptomatic CLL.",
        ),
        ClinicalVariant(
            "Pancreatic adenocarcinoma, borderline resectable (C25.9)",
            "Neoadjuvant FOLFIRINOX",
            "CA 19-9 890 U/mL; encasement of SMV <180° on CT.",
            "Neoadjuvant therapy to improve resectability.",
        ),
        ClinicalVariant(
            "Endometrial cancer, high-grade (C54.1)",
            "Adjuvant vaginal brachytherapy",
            "Stage IB grade 3; LVSI present on pathology.",
            "Brachytherapy reduces local recurrence in high-intermediate risk.",
        ),
        ClinicalVariant(
            "Renal cell carcinoma, metastatic clear cell (C64.9)",
            "Nivolumab plus cabozantinib",
            "Lung nodules new on CT; prior nephrectomy 2023.",
            "IO/TKI combination first-line for advanced RCC.",
        ),
    ],
    "surgical": [
        ClinicalVariant(
            "Morbid obesity with BMI 43 (E66.01)",
            "Roux-en-Y gastric bypass",
            "BMI 43 with OSA (AHI 32) and fatty liver; supervised diet 6 months documented.",
            "Bariatric surgery after supervised weight-loss attempt per policy.",
        ),
        ClinicalVariant(
            "Symptomatic uterine fibroids (D25.9)",
            "Myomectomy for fertility preservation",
            "Heavy bleeding Hgb 9.8; failed hormonal management; desires pregnancy.",
            "Myomectomy when fertility preservation is goal.",
        ),
        ClinicalVariant(
            "Deviated nasal septum with obstruction (J34.2)",
            "Septoplasty",
            "Failed intranasal steroids 4 months; CT septal deviation 80%.",
            "Surgery after failed medical management of obstruction.",
        ),
        ClinicalVariant(
            "Symptomatic cholelithiasis (K80.20)",
            "Laparoscopic cholecystectomy",
            "Recurrent biliary colic; ultrasound stones with gallbladder wall thickening.",
            "Cholecystectomy for symptomatic gallstones.",
        ),
        ClinicalVariant(
            "Ingrown toenail, recurrent (L60.0)",
            "Partial nail matrixectomy",
            "Three infections in 12 months; failed conservative podiatry care.",
            "Matrixectomy for recurrent ingrown nail.",
        ),
        ClinicalVariant(
            "Gynecomastia, persistent adolescent (N62)",
            "Subcutaneous mastectomy",
            "Tanner V, persistence 24 months, psychosocial impairment documented.",
            "Surgical correction when persistent after puberty.",
        ),
        ClinicalVariant(
            "Varicose veins with CEAP C4 disease (I83.10)",
            "Endovenous ablation",
            "Venous stasis changes; failed compression 3 months; reflux on duplex.",
            "Ablation for symptomatic saphenous reflux.",
        ),
        ClinicalVariant(
            "Chronic tonsillitis (J35.01)",
            "Tonsillectomy",
            "Seven episodes in 12 months per ENT records.",
            "Tonsillectomy for recurrent strep-documented tonsillitis.",
        ),
        ClinicalVariant(
            "Trigger finger, ring finger (M65.30)",
            "A1 pulley release",
            "Locking daily; failed steroid injection twice.",
            "Release after failed injections.",
        ),
        ClinicalVariant(
            "Breast hypertrophy with macromastia symptoms (N62)",
            "Reduction mammaplasty",
            "Shoulder grooving, intertrigo; 6 months PT for neck pain failed.",
            "Reduction for symptomatic macromastia after conservative measures.",
        ),
        ClinicalVariant(
            "Chronic sinusitis (J32.9)",
            "Functional endoscopic sinus surgery",
            "CT opacification; failed saline, steroids, and antibiotic courses.",
            "FESS after maximal medical therapy.",
        ),
        ClinicalVariant(
            "Pilonidal disease, recurrent (L05.01)",
            "Excision with flap closure",
            "Three flares in 18 months; failed wound care.",
            "Surgical excision for recurrent pilonidal disease.",
        ),
    ],
    "imaging": [
        ClinicalVariant(
            "Cervical strain after fall; rule out cord injury (S13.4XXA)",
            "MRI cervical spine without contrast",
            "ED visit with paresthesias; midline tenderness; X-ray negative.",
            "MRI appropriate with neurologic symptoms after trauma.",
        ),
        ClinicalVariant(
            "Lumbar disc herniation, suspected (M51.26)",
            "MRI lumbar spine without contrast",
            "Radicular pain 6 weeks; failed PT; straight-leg raise positive.",
            "MRI when conservative care fails with radiculopathy.",
        ),
        ClinicalVariant(
            "Pulmonary embolism, suspected low-intermediate risk (I26.99)",
            "CT pulmonary angiography",
            "Wells score 4.5; hypoxia 91% on room air; D-dimer elevated.",
            "CTA standard for suspected PE with elevated pre-test probability.",
        ),
        ClinicalVariant(
            "Headache with new neurologic deficit, subacute (R51.9)",
            "MRI brain with and without contrast",
            "New left facial numbness; migraine history but exam changed.",
            "MRI warranted with new focal neurologic findings.",
        ),
        ClinicalVariant(
            "Incidental adrenal nodule 2.8 cm (E27.8)",
            "Adrenal protocol CT",
            "Hypertension difficult to control; Hounsfield units indeterminate on prior CT.",
            "Adrenal CT characterization per incidentaloma guidelines.",
        ),
        ClinicalVariant(
            "Hip pain, non-arthritic suspicion (M25.551)",
            "MRI hip without contrast",
            "X-ray normal; groin pain with sport limitation 4 months.",
            "MRI sensitive for labral and soft-tissue hip pathology.",
        ),
        ClinicalVariant(
            "Renal colic, recurrent (N23)",
            "Non-contrast CT abdomen/pelvis (CT KUB)",
            "Three stone episodes; hematuria; ultrasound inconclusive.",
            "CT KUB gold standard for suspected nephrolithiasis.",
        ),
        ClinicalVariant(
            "Breast lump, BI-RADS 0 (N63.0)",
            "Diagnostic mammogram plus targeted ultrasound",
            "Palpable 1.2 cm mass; age 44; family history breast cancer.",
            "Diagnostic imaging required after inconclusive screening.",
        ),
        ClinicalVariant(
            "Scrotal pain, rule out torsion vs epididymitis (N50.9)",
            "Scrotal ultrasound with Doppler",
            "Acute onset pain 8 hours; UA negative; cremasteric reflex present.",
            "Ultrasound urgent for acute scrotum.",
        ),
        ClinicalVariant(
            "Abdominal aortic aneurysm surveillance (I71.4)",
            "Surveillance abdominal ultrasound",
            "Known 4.8 cm AAA; prior scan 6 months ago at 4.5 cm.",
            "Surveillance imaging per AAA guidelines.",
        ),
        ClinicalVariant(
            "Shoulder instability MRI (M25.311)",
            "MRI shoulder without contrast",
            "Recurrent subluxation; exam apprehension positive.",
            "MRI defines labral/ligament injury pre-operatively.",
        ),
        ClinicalVariant(
            "Sinus headache with vision changes (G44.1)",
            "MRI orbits and brain",
            "Proptosis exam; diplopia on lateral gaze.",
            "Imaging rules out orbital apex pathology.",
        ),
    ],
    "infusion_specialty_rx": [
        ClinicalVariant(
            "Crohn's disease, moderate to severe (K50.90)",
            "Ustekinumab (Stelara) maintenance infusion",
            "Anti-TNF failure (infliximab) with documented loss of response; calprotectin 420 mcg/g.",
            "Switch biologic class after anti-TNF failure.",
        ),
        ClinicalVariant(
            "Rheumatoid arthritis, seropositive (M06.9)",
            "Upadacitinib (Rinvoq) after methotrexate",
            "Methotrexate 20 mg weekly ×6 months; DAS28 5.4; sulfasalazine trial failed.",
            "JAK inhibitor after conventional DMARD failure.",
        ),
        ClinicalVariant(
            "Plaque psoriasis, moderate (L40.0)",
            "Adalimumab (Humira)",
            "BSA 12%; failed phototherapy 12 weeks and topical steroids.",
            "Biologic indicated with moderate BSA after topicals.",
        ),
        ClinicalVariant(
            "Relapsing multiple sclerosis (G35)",
            "Ocrelizumab infusion",
            "Two clinical relapses 2024–2025; MRI new T2 lesions despite teriflunomide.",
            "High-efficacy DMT after breakthrough on platform therapy.",
        ),
        ClinicalVariant(
            "Psoriatic arthritis (L40.50)",
            "Secukinumab (Cosentyx)",
            "Swollen joints 8; failed methotrexate; psoriasis BSA 5%.",
            "IL-17 inhibitor for PsA after DMARD failure.",
        ),
        ClinicalVariant(
            "Systemic lupus erythematosus, active (M32.10)",
            "Belimumab (Benlysta)",
            "SLEDAI 10; arthritis and rash despite hydroxychloroquine and mycophenolate.",
            "Add-on biologic for active SLE on background therapy.",
        ),
        ClinicalVariant(
            "Myasthenia gravis, generalized (G70.00)",
            "Eculizumab (Soliris)",
            "Positive acetylcholine receptor antibodies; failed pyridostigmine and steroids.",
            "Complement inhibitor for refractory gMG.",
        ),
        ClinicalVariant(
            "Hereditary angioedema (D84.1)",
            "Lanadelumab prophylaxis",
            "Monthly attacks; C4 chronically low; failed androgens due to side effects.",
            "Prophylactic monoclonal standard for HAE.",
        ),
        ClinicalVariant(
            "Pemphigus vulgaris (L10.0)",
            "Rituximab infusion",
            "Failed high-dose prednisone taper attempts; mucosal erosions persist.",
            "Rituximab for refractory pemphigus.",
        ),
        ClinicalVariant(
            "Immune thrombocytopenia, chronic (D69.3)",
            "Romiplostim (Nplate)",
            "Platelets 18k despite steroids and IVIG trials.",
            "TPO agonist after first-line ITP therapies.",
        ),
        ClinicalVariant(
            "Osteoporosis with vertebral fracture (M80.08XA)",
            "Denosumab (Prolia)",
            "Failed oral bisphosphonate due to intolerance; T-score -3.0 spine.",
            "Denosumab when oral bisphosphonates not tolerated.",
        ),
        ClinicalVariant(
            "Dermatomyositis with weakness (M33.10)",
            "IV immunoglobulin (IVIG)",
            "CK 3200 U/L; proximal weakness; failed methotrexate.",
            "IVIG for refractory inflammatory myopathy.",
        ),
    ],
    "womens_health": [
        ClinicalVariant(
            "Stage IV endometriosis (N80.4)",
            "Laparoscopic excision of endometriosis",
            "Dysmenorrhea 9/10; failed OCP and GnRH agonist trial 6 months.",
            "Excision for severe endometriosis after medical failure.",
        ),
        ClinicalVariant(
            "Polycystic ovary syndrome with infertility (E28.2)",
            "Letrozole ovulation induction",
            "Anovulatory cycles; failed clomiphene 100 mg ×3 cycles.",
            "Letrozole second-line for ovulation induction.",
        ),
        ClinicalVariant(
            "Pelvic floor dysfunction postpartum (N81.9)",
            "Pelvic floor physical therapy (12 visits)",
            "Stress incontinence postpartum; levator avulsion on ultrasound.",
            "PFPT first-line for postpartum pelvic floor symptoms.",
        ),
        ClinicalVariant(
            "Uterine prolapse, symptomatic (N81.2)",
            "Pessary fitting plus surgical consult",
            "Stage II prolapse; bulge symptoms; failed kegel program.",
            "Pessary or surgery for symptomatic prolapse.",
        ),
        ClinicalVariant(
            "Recurrent bacterial vaginosis (N76.0)",
            "Extended suppressive metronidazole course",
            "Four episodes in 12 months; failed single courses.",
            "Suppressive therapy for recurrent BV.",
        ),
        ClinicalVariant(
            "Primary dysmenorrhea, severe (N94.4)",
            "Hormonal IUD (levonorgestrel 52 mg)",
            "NSAIDs inadequate; absent secondary causes on ultrasound.",
            "IUD effective for dysmenorrhea.",
        ),
        ClinicalVariant(
            "Ovarian cyst, persistent 6 cm (N83.202)",
            "Laparoscopic cystectomy",
            "Simple cyst 6.2 cm persistent ×3 cycles; pain with intercourse.",
            "Surgery for persistent symptomatic cyst.",
        ),
        ClinicalVariant(
            "Menorrhagia due to adenomyosis (N80.0)",
            "Endometrial ablation",
            "Hgb 10.1; failed tranexamic acid and OCP; no fibroid on MRI.",
            "Ablation when fertility complete and medical therapy fails.",
        ),
        ClinicalVariant(
            "Vulvodynia, generalized (N94.818)",
            "Vulvar vestibulitis physical therapy protocol",
            "6 months topical therapy failed; Q-tip test positive.",
            "Multimodal therapy for vulvodynia.",
        ),
        ClinicalVariant(
            "Fibrocystic breast pain, severe (N60.19)",
            "Diagnostic imaging and cyst aspiration if indicated",
            "New focal pain; ultrasound recommended by PCP.",
            "Imaging excludes malignancy in focal breast pain.",
        ),
        ClinicalVariant(
            "Gestational diabetes on insulin (O24.414)",
            "Continuous glucose monitoring during pregnancy",
            "Postprandial glucose >140 mg/dL on insulin; hypoglycemia episodes.",
            "CGM improves glycemic control in insulin-requiring GDM.",
        ),
        ClinicalVariant(
            "Chronic pelvic pain, suspected endometriosis (R10.2)",
            "Diagnostic laparoscopy",
            "Chronic pain 18 months; MRI inconclusive; failed NSAIDs and hormones.",
            "Diagnostic laparoscopy when imaging negative but suspicion high.",
        ),
    ],
    "neurology": [
        ClinicalVariant(
            "Chronic migraine without aura (G43.709)",
            "Erenumab (Aimovig) preventive therapy",
            "15 headache days/month; failed topiramate 100 mg, propranolol 80 mg, and three triptans.",
            "CGRP inhibitor after multiple preventive failures.",
        ),
        ClinicalVariant(
            "Relapsing-remitting multiple sclerosis (G35)",
            "Ocrelizumab continuation beyond policy duration cap",
            "No relapses 14 months; stable MRI; prior breakthrough on dimethyl fumarate.",
            "Continuation standard when disease stable on effective DMT.",
        ),
        ClinicalVariant(
            "Focal epilepsy, drug-resistant (G40.019)",
            "Lacosamide add-on therapy",
            "Breakthrough seizures on levetiracetam and lamotrigine; EEG focal temporal spikes.",
            "Add-on AED when dual therapy inadequate.",
        ),
        ClinicalVariant(
            "Idiopathic intracranial hypertension (G93.2)",
            "Optic nerve sheath fenestration",
            "Papilledema grade III; visual field loss; failed acetazolamide 2 g.",
            "Surgical intervention when vision threatened.",
        ),
        ClinicalVariant(
            "Parkinson disease, motor fluctuations (G20)",
            "Duopa pump evaluation",
            "Off-time 6 hours daily despite optimized oral levodopa.",
            "Advanced therapy for motor fluctuations.",
        ),
        ClinicalVariant(
            "Amyotrophic lateral sclerosis (G12.21)",
            "Riluzole and multidisciplinary ALS clinic",
            "Progressive weakness; EMG active denervation in three regions.",
            "Riluzole and supportive care standard for ALS.",
        ),
        ClinicalVariant(
            "Trigeminal neuralgia, classic (G50.0)",
            "Microvascular decompression referral",
            "Carbamazepine 800 mg daily with breakthrough lancinating pain.",
            "MVD considered when medical therapy inadequate.",
        ),
        ClinicalVariant(
            "Normal pressure hydrocephalus, suspected (G91.2)",
            "High-volume lumbar puncture trial",
            "Gait apraxia, incontinence, cognitive slowing; Evans index >0.3.",
            "LP trial before ventricular shunting.",
        ),
        ClinicalVariant(
            "Restless legs syndrome, refractory (G25.81)",
            "Pramipexole titration",
            "Ferritin 45 ng/mL; failed gabapentin 300 mg TID.",
            "Dopamine agonist when alpha-2-delta ligand insufficient.",
        ),
        ClinicalVariant(
            "Carpal tunnel with neurology referral (G56.00)",
            "Nerve conduction study and splinting",
            "Nocturnal paresthesias; thenar numbness.",
            "NCS confirms diagnosis and guides surgery timing.",
        ),
        ClinicalVariant(
            "Post-concussion syndrome (G44.309)",
            "Multidisciplinary concussion clinic program",
            "Headache and dizziness 3 months post-MVA; vestibular therapy started.",
            "Structured rehab for persistent post-concussive symptoms.",
        ),
        ClinicalVariant(
            "Small fiber neuropathy, idiopathic (G62.89)",
            "Skin biopsy for intraepidermal nerve fiber density",
            "Burning feet; normal large-fiber NCS; autonomic symptoms mild.",
            "Biopsy confirms small fiber diagnosis guiding treatment.",
        ),
    ],
}


def _denial_seeds(sub_tactic: str, variant: ClinicalVariant, insurer: str) -> tuple[str, str]:
    """Return (denial_rationale_seed, rebuttal_seed) aligned to sub_tactic."""
    tx = variant.treatment_requested
    dx = variant.diagnosis
    seeds: dict[str, tuple[str, str]] = {
        "step_therapy_missing": (
            f"{insurer} medical policy requires documented failure of prerequisite therapies before {tx}. "
            f"Submitted records do not establish failure of required lower-cost options for {dx}.",
            f"{variant.rebuttal_core} {variant.clinical_facts}",
        ),
        "conservative_treatment_required": (
            f"Coverage requires a defined course of conservative therapy before {tx}. "
            f"Documentation does not show the required duration or type of conservative care.",
            f"{variant.clinical_facts} The requested {tx} is appropriate after documented conservative failure.",
        ),
        "frequency_excessive": (
            f"The requested frequency exceeds plan guidelines for {dx}. "
            f"Additional visits are not medically necessary at this cadence.",
            f"{variant.rebuttal_core} Clinical notes show worsening despite prior visits within guideline limits.",
        ),
        "level_of_care_too_high": (
            f"A lower level of care is appropriate for {dx}; {tx} exceeds what is required. "
            f"Outpatient management has not been exhausted per clinical guidelines.",
            f"{variant.clinical_facts} Symptoms support the higher level of care requested.",
        ),
        "not_evidence_based": (
            f"{tx} is not considered evidence-based for {dx} under current medical policy. "
            f"Published criteria do not support authorization.",
            f"{variant.rebuttal_core} Contemporary guidelines and trial data support use in this clinical context.",
        ),
        "duration_excessive": (
            f"The duration of {tx} exceeds plan limits without new clinical review. "
            f"Continuation requires updated documentation not received.",
            f"{variant.clinical_facts} Ongoing treatment prevents relapse documented in chart.",
        ),
        "guideline_mis_cite": (
            f"Clinical criteria for {tx} are not met per the cited utilization guideline module for {dx}. "
            f"The request does not satisfy threshold requirements in the referenced criteria set.",
            f"The insurer applied the wrong guideline module; {variant.rebuttal_core}",
        ),
        "missing_peer_to_peer": (
            f"Prior authorization for {tx} is denied because a required peer-to-peer review was not completed in the allowed window. "
            f"Clinical information may be discussed during appeal submission.",
            f"Three scheduling attempts were documented; {variant.clinical_facts}",
        ),
        "formulary_tier_dispute": (
            f"{tx} is non-preferred; a formulary alternative must be tried for {dx}. "
            f"A lower-tier agent is available without demonstrated failure of the preferred option.",
            f"{variant.clinical_facts} Prior biologic failure/contraindication supports exception.",
        ),
        "out_of_network_no_authorization": (
            f"{tx} with an out-of-network provider is not covered without a gap exception. "
            f"In-network alternatives are available.",
            f"No in-network surgeon performs high-volume specialized excision; {variant.rebuttal_core}",
        ),
        "continuation_of_care_lapsed": (
            f"Continuation of {tx} requires an active prior authorization; the prior auth lapsed. "
            f"A new authorization must be submitted.",
            f"Stable disease on therapy 12+ months; lapse was administrative, not clinical. {variant.clinical_facts}",
        ),
        "emergency_retroactive_auth": (
            f"Emergency imaging/treatment for {dx} is denied for lack of prior authorization. "
            f"Retroactive authorization is not granted for non-emergent services.",
            f"ED presentation met prudent layperson standard; {variant.clinical_facts}",
        ),
        "modality_substitution": (
            f"A less costly modality is appropriate before {tx} for {dx}. "
            f"Plan policy requires step-down diagnostic or therapeutic approach.",
            f"{variant.rebuttal_core} Patient factors make substituted modality unsafe or inadequate.",
        ),
        "visit_limit_exceeded": (
            f"Annual visit limit for services treating {dx} has been exceeded. "
            f"Additional visits are not a covered benefit this plan year.",
            f"{variant.rebuttal_core} Parity and medical necessity support continued visits.",
        ),
    }
    return seeds.get(
        sub_tactic,
        (
            f"Requested {tx} does not meet medical necessity criteria for {dx}.",
            f"{variant.rebuttal_core} {variant.clinical_facts}",
        ),
    )


def build_scenario_brief(
    index: int,
    cell: dict[str, str],
    patterns: list[dict[str, Any]],
) -> dict[str, Any]:
    """P1 output aligned to matrix specialty (not sub_tactic alone)."""
    specialty = cell["specialty"]
    variants = SPECIALTY_VARIANTS.get(specialty)
    if not variants:
        raise ValueError(f"No variants for specialty {specialty}")
    variant = variants[(index - 11) % len(variants)]
    age = _age_in_band(cell["patient_age_band"], index)
    plan = "fully_insured"
    for p in patterns:
        if p.get("id") == "plan_exclusion_overrides_state_mandate":
            plan = "fully_insured"
            break
    else:
        plan = "fully_insured" if (index % 5 == 0) else "self_funded"

    employer = None
    if cell["patient_age_band"] == "71+":
        employer = (
            "still actively employed as a senior professional on a large-group "
            "employer-sponsored commercial PPO"
        )
        plan = "fully_insured"

    flaw_types: list[str] = []
    for p in patterns[:2]:
        flaw_types.extend(p.get("realistic_flaws", [])[:2])
    if not flaw_types:
        flaw_types = ["vague guideline citation", "missing external review notice"]

    denial_seed, rebuttal_seed = _denial_seeds(
        cell["sub_tactic"], variant, cell["insurer"]
    )
    difficulty = [1, 3, 5][index % 3]

    return {
        "matrix_cell": dict(cell),
        "diagnosis": variant.diagnosis,
        "treatment_requested": variant.treatment_requested,
        "denial_rationale_seed": denial_seed,
        "rebuttal_seed": rebuttal_seed,
        "patient_age": age,
        "patient_gender": cell["patient_gender"],
        "plan_funding_type": plan,
        "employer_archetype": employer,
        "intended_appeal_difficulty": difficulty,
        "intended_flaw_types": flaw_types[:3],
        "intended_flaw_categories": (
            list({p.get("category", "procedural_disclosure") for p in patterns[:2]})
            or ["procedural_disclosure"]
        ),
        "_clinical_facts": variant.clinical_facts,
        "_patterns": patterns,
    }
