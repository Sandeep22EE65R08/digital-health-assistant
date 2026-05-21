"""Rule-based safe responder used when no AI API key is configured (Demo mode).

It never diagnoses — only summarizes, suggests a specialist type, flags emergencies,
and produces the same HTML structure the frontend renders for AI responses.
"""
from __future__ import annotations

EMERGENCY_KEYWORDS = [
    "chest pain", "shortness of breath", "difficulty breathing", "can't breathe",
    "unconscious", "loss of consciousness", "fainted", "seizure", "stroke",
    "paralysis", "slurred speech", "severe bleeding", "heavy bleeding",
    "suicidal", "kill myself", "head injury", "very high fever", "confused",
    "blue lips", "low oxygen", "cardiac arrest", "heart attack",
]

SPECIALIST_RULES = [
    (["chest", "heart", "palpitation", "bp", "blood pressure"],
     "Cardiologist", "for evaluation of heart and circulation symptoms"),
    (["skin", "rash", "acne", "itch", "eczema"],
     "Dermatologist", "for skin-related concerns"),
    (["joint", "bone", "back pain", "knee", "fracture"],
     "Orthopedic specialist", "for bone, joint, or muscle problems"),
    (["thyroid", "tsh", "hormone", "diabetes", "sugar"],
     "Endocrinologist", "for hormone or metabolic concerns"),
    (["sad", "anxious", "depress", "stress", "panic", "sleep"],
     "Psychiatrist or Psychologist", "for mental health and emotional well-being"),
    (["child", "baby", "infant", "kid"],
     "Pediatrician", "because the concern relates to a child"),
    (["eye", "vision", "blurred"],
     "Ophthalmologist", "for eye and vision concerns"),
    (["ear", "nose", "throat", "sore throat", "sinus"],
     "ENT specialist", "for ear, nose, or throat symptoms"),
    (["period", "menstru", "pregnan", "pcos"],
     "Gynecologist", "for women's health concerns"),
    (["stomach", "abdomen", "vomit", "diarrhea", "loose motion", "acidity"],
     "Gastroenterologist", "for digestion-related symptoms"),
]

TEST_RULES = [
    (["tired", "weak", "fatigue", "pale"],
     ["CBC", "Vitamin D", "Vitamin B12", "Thyroid Profile (TSH)"]),
    (["sugar", "diabetes", "thirst", "frequent urination"],
     ["Fasting Blood Sugar", "HbA1c"]),
    (["thyroid", "weight gain", "weight loss"],
     ["Thyroid Profile (TSH, T3, T4)"]),
    (["fever"], ["CBC", "Malaria/Dengue panel (as advised)"]),
    (["chest", "bp", "blood pressure"],
     ["ECG", "Lipid Profile", "Blood Pressure check"]),
    (["liver", "jaundice"], ["Liver Function Test (LFT)"]),
    (["kidney", "urine"], ["Kidney Function Test (KFT)", "Urine Routine"]),
    (["headache", "migraine"], ["Blood Pressure check", "Eye check-up", "CBC"]),
    (["cough", "cold", "throat"], ["CBC", "Throat swab (if advised)"]),
    (["skin", "rash", "itch"], ["Allergy panel (if advised)", "CBC"]),
    (["joint", "knee", "back pain"], ["Vitamin D", "Calcium", "X-ray (if advised)"]),
]

# Keyword -> list of plain-language possible causes (educational only).
CAUSE_RULES = [
    (["headache", "migraine"], [
        "Tension or stress-related headache",
        "Dehydration or poor sleep",
        "Eye strain or refractive error",
        "Migraine or sinus-related causes",
    ]),
    (["fever"], [
        "Common viral infection (e.g. flu)",
        "Seasonal infections (dengue, malaria — region dependent)",
        "Throat or urinary infection",
    ]),
    (["cough", "cold", "throat", "sore throat"], [
        "Viral upper respiratory infection",
        "Allergy or post-nasal drip",
        "Throat irritation from dryness or pollution",
    ]),
    (["tired", "weak", "fatigue", "pale"], [
        "Iron deficiency or anemia",
        "Vitamin D or B12 deficiency",
        "Thyroid imbalance",
        "Poor sleep or high stress",
    ]),
    (["chest", "heart", "palpitation"], [
        "Acidity or muscular chest pain",
        "Anxiety-related palpitations",
        "A cardiac cause that a doctor should rule out",
    ]),
    (["stomach", "abdomen", "vomit", "diarrhea", "loose motion", "acidity"], [
        "Indigestion or acidity",
        "Food-borne infection (gastroenteritis)",
        "Dietary intolerance",
    ]),
    (["sugar", "diabetes", "thirst", "frequent urination"], [
        "Possible blood sugar imbalance",
        "Dehydration",
        "Urinary tract infection",
    ]),
    (["thyroid", "weight gain", "weight loss"], [
        "Thyroid hormone imbalance",
        "Nutritional or lifestyle factors",
        "Hormonal changes",
    ]),
    (["skin", "rash", "itch", "acne", "eczema"], [
        "Allergic reaction or contact irritation",
        "Eczema or fungal infection",
        "Hormonal acne",
    ]),
    (["joint", "knee", "back pain", "bone"], [
        "Muscle strain or poor posture",
        "Vitamin D or calcium deficiency",
        "Arthritis-related causes",
    ]),
    (["sad", "anxious", "depress", "stress", "panic", "sleep"], [
        "Stress or anxiety",
        "Poor sleep quality",
        "Underlying mood-related condition",
    ]),
    (["eye", "vision", "blurred"], [
        "Refractive error or eye strain",
        "Dry eyes",
        "An issue requiring an eye check-up",
    ]),
    (["ear", "nose", "sinus"], [
        "Allergy or sinus irritation",
        "Common cold",
        "Ear or sinus infection",
    ]),
]


def _detect_severity(text: str) -> str:
    t = text.lower()
    if any(k in t for k in EMERGENCY_KEYWORDS):
        return "Emergency"
    if any(k in t for k in ("severe", "intense", "worsening", "cannot", "can't")):
        return "Urgent"
    if any(k in t for k in ("mild", "slight", "little", "sometimes")):
        return "Mild"
    return "Moderate"


def _pick_specialist(text: str):
    t = text.lower()
    for keywords, who, why in SPECIALIST_RULES:
        if any(k in t for k in keywords):
            return who, why
    return None, None


def _collect_tests(text: str) -> list[str]:
    t = text.lower()
    seen: list[str] = []
    for keywords, tests in TEST_RULES:
        if any(k in t for k in keywords):
            for x in tests:
                if x not in seen:
                    seen.append(x)
    return seen


def _collect_causes(text: str) -> list[str]:
    t = text.lower()
    seen: list[str] = []
    for keywords, causes in CAUSE_RULES:
        if any(k in t for k in keywords):
            for c in causes:
                if c not in seen:
                    seen.append(c)
    if not seen:
        seen = [
            "Common viral or seasonal causes",
            "Lifestyle factors (sleep, stress, diet, hydration)",
            "Possible nutritional deficiency",
            "An underlying condition that a doctor can evaluate",
        ]
    return seen[:6]


def _summary_for(text: str, base: str) -> str:
    """Echo the user's symptoms in the summary so each response feels specific."""
    trimmed = " ".join(text.split())
    if not trimmed:
        return base
    if len(trimmed) > 220:
        trimmed = trimmed[:217] + "…"
    return f"You described: <em>{trimmed}</em>. {base}"


def _labels(language: str) -> dict:
    lang = (language or "English").lower()
    if lang.startswith("hindi"):
        return {
            "summary": "सारांश", "causes": "संभावित कारण", "severity": "गंभीरता स्तर",
            "doctor": "सुझाया गया डॉक्टर", "tests": "सुझाए गए टेस्ट",
            "lifestyle": "जीवनशैली सुझाव", "emergency": "आपातकालीन चेतावनी",
            "disclaimer": "अस्वीकरण",
            "disclaimerText": "यह सहायक केवल शैक्षिक मार्गदर्शन देता है और किसी योग्य चिकित्सक का विकल्प नहीं है।",
            "defaultDoc": "जनरल फिजिशियन", "defaultWhy": "सामान्य लक्षणों की जाँच के लिए",
            "base": "आपके लक्षण कई सामान्य कारणों से जुड़े हो सकते हैं। कृपया घबराएँ नहीं।",
        }
    if lang.startswith("hinglish"):
        return {
            "summary": "Summary", "causes": "Possible Causes", "severity": "Severity",
            "doctor": "Suggested Doctor", "tests": "Suggested Tests",
            "lifestyle": "Lifestyle Tips", "emergency": "Emergency Warning",
            "disclaimer": "Disclaimer",
            "disclaimerText": "Yeh assistant sirf educational guidance deta hai — doctor ka replacement nahi hai.",
            "defaultDoc": "General Physician", "defaultWhy": "general symptoms check karne ke liye",
            "base": "Aapke symptoms common causes se related ho sakte hain. Please ghabraayein nahi.",
        }
    return {
        "summary": "Summary", "causes": "Possible Causes", "severity": "Severity Level",
        "doctor": "Suggested Doctor", "tests": "Suggested Tests",
        "lifestyle": "Lifestyle Suggestions", "emergency": "Emergency Warning",
        "disclaimer": "Disclaimer",
        "disclaimerText": "This assistant provides educational guidance only and is not a replacement for professional medical diagnosis or treatment.",
        "defaultDoc": "General Physician", "defaultWhy": "for evaluation of general symptoms",
        "base": "Your symptoms may be associated with several common causes. Please stay calm.",
    }


def analyze(intake: dict) -> str:
    """Return an HTML fragment with the structured safe response."""
    text = " ".join(filter(None, [intake.get("symptoms"), intake.get("reportText")]))
    t = _labels(intake.get("language", "English"))
    severity = _detect_severity(text)
    who, why = _pick_specialist(text)
    who = who or t["defaultDoc"]
    why = why or t["defaultWhy"]
    tests = _collect_tests(text)

    lifestyle = [
        "Stay well hydrated.",
        "Maintain regular sleep (7–8 hours).",
        "Eat balanced, home-cooked meals.",
        "Avoid self-medication.",
    ]
    possible_causes = _collect_causes(text)

    parts = [
        f"<h4>{t['summary']}</h4><p>{_summary_for(text, t['base'])}</p>",
        f"<h4>{t['causes']}</h4><ul>" + "".join(f"<li>{c}</li>" for c in possible_causes) + "</ul>",
        f"<h4>{t['severity']} <span class=\"severity-tag sev-{severity}\">{severity}</span></h4>",
        f"<h4>{t['doctor']}</h4><p>{who} — {why}.</p>",
    ]
    if tests:
        parts.append(f"<h4>{t['tests']}</h4><ul>" + "".join(f"<li>{x}</li>" for x in tests) + "</ul>")
    parts.append(f"<h4>{t['lifestyle']}</h4><ul>" + "".join(f"<li>{x}</li>" for x in lifestyle) + "</ul>")
    if severity == "Emergency":
        parts.append(
            f"<h4>⚠️ {t['emergency']}</h4><p>Your symptoms may require urgent medical attention. "
            "Please visit a nearby hospital or contact a healthcare professional immediately.</p>"
        )
    parts.append(f"<h4>{t['disclaimer']}</h4><p>{t['disclaimerText']}</p>")
    return "".join(parts)
