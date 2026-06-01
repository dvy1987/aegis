import type { CaseSummary } from "@/lib/types";

export const CASES: CaseSummary[] = [
  {
    case_id: "test_case_01_uhc_mednec",
    insurer: "UHC",
    denial_type: "Medical necessity",
    headline: "Bariatric revision denied pending maximum conservative therapy",
    denial_letter_text:
      "Dear Member,\n\nWe have reviewed the request for a Bariatric Surgery Revision. Based on UnitedHealthcare's Medical Management Guidelines, this request is denied.\n\nWhile we recognize you are experiencing severe acid reflux following a previous gastric sleeve procedure, the clinical information provided does not demonstrate that maximum medical management (such as high-dose proton pump inhibitors and lifestyle modifications) has been attempted and failed for at least 6 months. Therefore, surgical revision is not considered medically necessary at this time as a first-line treatment for your reflux.",
    clinical_context:
      "Patient had a gastric sleeve 5 years ago. Now experiencing severe GERD causing esophageal strictures and Barrett's esophagus (pre-cancerous changes). The surgeon notes that PPIs will not fix the anatomical issue causing the bile reflux, making conservative therapy useless and dangerous.",
  },
  {
    case_id: "test_case_02_aetna_priorauth",
    insurer: "Aetna",
    denial_type: "Prior authorization",
    headline: "Emergency wrist MRI denied for missing out-of-network authorization",
    denial_letter_text:
      "Dear Member,\n\nWe are denying coverage for the MRI of the wrist performed on 06/02/2026 by an out-of-network radiology center.\n\nYour plan requires prior authorization for all advanced imaging, and specifically requires out-of-network services to receive a Network Exception authorization before the service is rendered. Our records indicate no such authorization was requested or approved. Because this was not a life-threatening emergency, you are responsible for the out-of-network charges.",
    clinical_context:
      "Patient fell skateboarding and went to an urgent care. X-rays were negative but the doctor suspected a scaphoid fracture (which can cause bone death if missed). The doctor sent him immediately to the imaging center next door. The center was out-of-network and did not run a prior auth because of the urgent nature of the referral.",
  },
  {
    case_id: "test_case_03_cigna_mednec",
    insurer: "Cigna",
    denial_type: "Medical necessity",
    headline: "Wegovy denied as a plan exclusion",
    denial_letter_text:
      "Dear Member,\n\nWe have reviewed your provider's request for Semaglutide (Wegovy). We are denying this request because it does not meet Cigna's coverage criteria.\n\nWhile Wegovy is FDA-approved for weight management, your specific employer-sponsored pharmacy benefit plan has a strict exclusion for all weight-loss medications. Additionally, you do not have a diagnosis of Type 2 Diabetes, which would be required for coverage of similar GLP-1 medications (like Ozempic) under your medical benefit. Therefore, this request is denied as a plan exclusion and is not medically necessary.",
    clinical_context:
      "Patient has struggled with weight and is on the verge of developing full-blown Type 2 Diabetes. The doctor prescribed Wegovy to prevent the onset of diabetes. The denial relies on a hard employer plan exclusion for 'weight loss drugs', forcing an appeal to argue the preventative medical necessity rather than cosmetic weight loss.",
  },
  {
    case_id: "test_case_04_uhc_priorauth",
    insurer: "UHC",
    denial_type: "Prior authorization",
    headline: "Inpatient rehabilitation denied based on outdated therapy notes",
    denial_letter_text:
      "Dear Member,\n\nWe received a prior authorization request to transfer you from acute hospital care to an Inpatient Rehabilitation Facility (IRF). We are denying this request.\n\nBased on UnitedHealthcare guidelines, admission to an IRF requires evidence that the patient can actively participate in and benefit from at least three (3) hours of intensive therapy per day. The clinical notes from your physical therapist in the hospital indicate you fatigued after 30 minutes of therapy yesterday. Therefore, we are authorizing a transfer to a Skilled Nursing Facility (SNF) instead, which provides a lower, less intensive level of care.",
    clinical_context:
      "Patient had a severe stroke but is highly motivated. The single day she fatigued after 30 minutes was the day immediately following her stroke. Since then, she has been doing 2 hours a day easily, but the hospital submitted the older notes. An SNF will not provide the intensive daily therapy needed for her to regain walking ability.",
  },
  {
    case_id: "test_case_05_aetna_mednec",
    insurer: "Aetna",
    denial_type: "Medical necessity",
    headline: "Speech therapy denied as developmental when trauma relapse is documented",
    denial_letter_text:
      "Dear Member,\n\nWe have reviewed the request for outpatient speech therapy. Based on Aetna's Clinical Policy Bulletin for Speech Therapy, this request is denied.\n\nYour plan only covers speech therapy when it is restorative in nature—meaning it is required to restore speech that was lost due to an illness, injury, or stroke (such as a traumatic brain injury). The clinical records indicate you have had a stutter since childhood, making this a developmental condition. Developmental speech therapy is excluded under your adult medical benefit. Therefore, the services are not covered.",
    clinical_context:
      "The patient did have a stutter as a child but had fully overcome it. He was recently in a severe car accident (trauma) and the stutter returned intensely, affecting his ability to work. The denial incorrectly categorizes it as purely developmental rather than a trauma-induced relapse needing restorative therapy.",
  },
  {
    case_id: "test_case_06_cigna_priorauth",
    insurer: "Cigna",
    denial_type: "Prior authorization",
    headline: "Emergency air ambulance denied for a 45-mile transfer during a heart attack",
    denial_letter_text:
      "Dear Member,\n\nWe are denying coverage for the Air Ambulance transport that occurred on 05/12/2026. \n\nAccording to Cigna guidelines, non-emergency inter-facility medical transport requires prior authorization. Furthermore, air ambulance transport is only covered when ground transport is medically contraindicated or the time required for ground transport would endanger the patient's life. Our records show the distance between the two hospitals was only 45 miles. Because prior authorization was not obtained and medical necessity for air over ground transport was not established, this claim is denied.",
    clinical_context:
      "The patient had a massive heart attack at a rural hospital that lacked cardiothoracic surgery capabilities. Ground transport would have taken 90 minutes due to severe mountain weather, risking permanent heart muscle death. The ER doctor ordered the helicopter immediately as a life-saving measure. The denial improperly categorizes it as non-emergency.",
  },
  {
    case_id: "test_case_07_uhc_mednec",
    insurer: "UHC",
    denial_type: "Medical necessity",
    headline: "Eating disorder IOP denied because patient is above weight threshold",
    denial_letter_text:
      "Dear Member,\n\nWe have reviewed the request for an Eating Disorder Intensive Outpatient Program (IOP). Based on UnitedHealthcare's Medical Necessity Guidelines and the APA practice guidelines, we are denying this request.\n\nThe clinical information indicates you are currently at 88% of your ideal body weight (IBW) and your vital signs are stable without severe bradycardia. Our guidelines require a patient to either be below 85% of IBW or exhibit acute medical instability (such as severe electrolyte imbalance) to qualify for an intensive eating disorder program. Because you do not meet these criteria, you can be safely managed in standard weekly outpatient therapy.",
    clinical_context:
      "The patient is medically stable only because her parents force-feed her, causing severe daily panic attacks. While her weight is technically 88% of IBW, she is actively losing 2-3 lbs a week and restricting heavily. Standard weekly therapy is failing to stop the rapid weight loss trajectory.",
  },
  {
    case_id: "test_case_08_aetna_priorauth",
    insurer: "Aetna",
    denial_type: "Prior authorization",
    headline: "BRCA genetic test denied for missing pre-test counseling session",
    denial_letter_text:
      "Dear Member,\n\nWe are denying coverage for the BRCA1 and BRCA2 genetic testing performed on 05/20/2026.\n\nAccording to Aetna policy, all genetic testing requires prior authorization and must be accompanied by genetic counseling from a certified genetic counselor. While your records indicate you have a first-degree relative with breast cancer, your provider did not submit a prior authorization request with documentation of the required pre-test genetic counseling session. Because this requirement was not met before the test was performed, the claim is denied.",
    clinical_context:
      "The patient's mother and sister both died of breast cancer before age 50. Her OB/GYN drew the blood for the BRCA test during her annual exam without realizing Aetna required a separate consultation with a certified genetic counselor first. The test is completely medically necessary, but denied on a procedural prior auth technicality.",
  },
  {
    case_id: "test_case_09_cigna_mednec",
    insurer: "Cigna",
    denial_type: "Medical necessity",
    headline: "Jaw surgery denied as cosmetic despite documented functional impairment",
    denial_letter_text:
      "Dear Member,\n\nWe have reviewed the request for Orthognathic Surgery (Bilateral Sagittal Split Osteotomy). Based on Cigna's Medical Coverage Policies, we are denying this request.\n\nThe clinical information provided indicates you have a malocclusion (bite misalignment). However, our guidelines consider orthognathic surgery to be cosmetic and not medically necessary unless there is evidence of significant functional impairment, such as documented malnutrition, severe sleep apnea, or an inability to chew/swallow that has caused documented weight loss. The records provided only note difficulty chewing and jaw pain, which does not meet the threshold for functional impairment.",
    clinical_context:
      "Patient has a severe underbite causing chronic TMJ pain, daily headaches, and difficulty chewing solid foods, which has caused him to adopt a liquid diet. The provider's initial submission did not explicitly include his weight logs or diet restrictions, leading Cigna to label the surgery 'cosmetic'.",
  },
  {
    case_id: "test_case_10_uhc_priorauth",
    insurer: "UHC",
    denial_type: "Prior authorization",
    headline: "Home health extension denied after agency missed reauthorization deadline",
    denial_letter_text:
      "Dear Member,\n\nWe received a claim for continued Home Health Care services (nursing and physical therapy) from 05/14/2026 to 05/28/2026. We are denying these services because they were not prior authorized.\n\nYour plan approved an initial two (2) week episode of Home Health Care following your hospital discharge. Any continued care beyond the initial episode requires a new prior authorization request with updated clinical notes demonstrating that you remain 'homebound' and require intermittent skilled care. We did not receive a request to extend these services before they were provided. Therefore, the continued visits are denied.",
    clinical_context:
      "The patient is 78, lives alone, and developed a minor wound infection requiring daily dressing changes by a nurse, preventing her from traveling to an outpatient clinic. The home health agency missed the deadline to file for the 3rd-week extension, but the services were absolutely critical to prevent sepsis and hospital readmission.",
  },
];
