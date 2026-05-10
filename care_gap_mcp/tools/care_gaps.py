"""Care gap finder — USPSTF-aligned rule engine + Gemini-authored rationale.

The rule engine deterministically identifies gaps so we never hallucinate one;
the LLM is only asked to author the *clinician-facing rationale* explaining why
this specific patient warrants action now. This is the AI factor: a rule engine
flags the gap, but only an LLM can produce the patient-specific reasoning that
a care manager would actually use.
"""
import os
from datetime import date, datetime, timezone
from typing import Any

from fhir.resources.patient import Patient

from po_fastmcp import FhirClient, get_fhir_context

# Conservative SNOMED/ICD-10 sets — small on purpose. Expanding requires
# clinical review; we don't want false positives.
SNOMED_DIABETES = {"44054006", "73211009", "46635009"}
SNOMED_HYPERTENSION = {"38341003", "59621000"}
ICD10_DIABETES_PREFIX = ("E10", "E11", "E13")
ICD10_HYPERTENSION_PREFIX = ("I10", "I11", "I12", "I13", "I15")

LOINC_A1C = "4548-4"
LOINC_SYSTOLIC = "8480-6"
CPT_COLONOSCOPY = {"45378", "45380", "45385"}
CPT_FIT = {"82270"}
CPT_MAMMOGRAM = {"77067", "77066", "77065"}


def register(mcp) -> None:
    mcp.tool(name="FindCareGaps")(find_care_gaps)


async def find_care_gaps() -> dict:
    """Identify USPSTF-aligned preventive care gaps for the current patient.

    Each gap has: id, title, severity, evidence (raw FHIR-derived facts that
    triggered the rule), and rationale (LLM-authored, one sentence, clinician-
    facing). Patients with no gaps return an empty list.
    """
    context = get_fhir_context()
    if context is None or not context.patient_id:
        return {"status": "error", "message": "FHIR context with patient_id is required."}

    client = FhirClient(context)

    patient_resource = await client.read("Patient", context.patient_id)
    if patient_resource is None:
        return {"status": "error", "message": "Patient not found."}
    patient = Patient.model_validate(patient_resource)
    age = _age(patient.birthDate)
    gender = (patient.gender or "").lower()

    conditions = await client.search(
        "Condition",
        {"patient": context.patient_id, "clinical-status": "active"},
        limit=100,
    )
    observations = await client.search(
        "Observation",
        {"patient": context.patient_id, "_sort": "-date"},
        limit=200,
    )
    procedures = await client.search(
        "Procedure",
        {"patient": context.patient_id, "_sort": "-date"},
        limit=100,
    )

    has_diabetes = _has_condition(conditions, SNOMED_DIABETES, ICD10_DIABETES_PREFIX)
    has_htn = _has_condition(conditions, SNOMED_HYPERTENSION, ICD10_HYPERTENSION_PREFIX)

    most_recent_a1c = _most_recent_observation(observations, LOINC_A1C)
    most_recent_systolic = _most_recent_observation(observations, LOINC_SYSTOLIC)
    most_recent_colon_screen = _most_recent_procedure(procedures, CPT_COLONOSCOPY | CPT_FIT)
    most_recent_mammogram = _most_recent_procedure(procedures, CPT_MAMMOGRAM)

    gaps: list[dict[str, Any]] = []

    # Diabetes A1c monitoring (every 6 months for active DM)
    if has_diabetes and _months_since(most_recent_a1c) > 6:
        gaps.append({
            "id": "diabetes-a1c-overdue",
            "title": "HbA1c overdue for diabetic patient",
            "severity": "high",
            "uspstf_grade": "A",
            "evidence": {
                "active_diabetes": True,
                "last_a1c_date": most_recent_a1c["date"] if most_recent_a1c else None,
                "last_a1c_value": most_recent_a1c["value"] if most_recent_a1c else None,
                "months_since_last_a1c": _months_since(most_recent_a1c),
            },
        })

    # Hypertension follow-up (BP every 12 months for active HTN)
    if has_htn and _months_since(most_recent_systolic) > 12:
        gaps.append({
            "id": "hypertension-bp-overdue",
            "title": "Blood pressure check overdue for hypertensive patient",
            "severity": "medium",
            "uspstf_grade": "A",
            "evidence": {
                "active_hypertension": True,
                "last_systolic_date": most_recent_systolic["date"] if most_recent_systolic else None,
                "last_systolic_value": most_recent_systolic["value"] if most_recent_systolic else None,
                "months_since_last_bp": _months_since(most_recent_systolic),
            },
        })

    # Colorectal screening (45–75, no colonoscopy in 10y or FIT in 1y)
    if age is not None and 45 <= age <= 75:
        years_since_colon = _months_since(most_recent_colon_screen) / 12
        cpt = (most_recent_colon_screen or {}).get("cpt")
        is_fit = cpt in CPT_FIT
        overdue = years_since_colon > (1 if is_fit else 10)
        if most_recent_colon_screen is None or overdue:
            gaps.append({
                "id": "colorectal-screening-overdue",
                "title": "Colorectal cancer screening overdue",
                "severity": "high",
                "uspstf_grade": "A",
                "evidence": {
                    "age": age,
                    "last_screening_date": (most_recent_colon_screen or {}).get("date"),
                    "last_screening_type": (most_recent_colon_screen or {}).get("label"),
                },
            })

    # Mammography (women 40–74, every 2 years)
    if gender == "female" and age is not None and 40 <= age <= 74:
        if most_recent_mammogram is None or _months_since(most_recent_mammogram) > 24:
            gaps.append({
                "id": "mammography-overdue",
                "title": "Mammography overdue",
                "severity": "high",
                "uspstf_grade": "B",
                "evidence": {
                    "age": age,
                    "gender": gender,
                    "last_mammogram_date": (most_recent_mammogram or {}).get("date"),
                },
            })

    # Author rationale for each gap with Gemini.
    for gap in gaps:
        gap["rationale"] = _author_rationale(gap, age, gender)

    return {
        "status": "success",
        "patient_id": context.patient_id,
        "age": age,
        "gender": gender,
        "gap_count": len(gaps),
        "gaps": gaps,
    }


# ── Rule helpers ──────────────────────────────────────────────────────────────

def _age(birth_date) -> int | None:
    if birth_date is None:
        return None
    if isinstance(birth_date, str):
        birth_date = datetime.fromisoformat(birth_date).date()
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def _has_condition(conditions: list, snomed_codes: set[str], icd10_prefixes: tuple) -> bool:
    for res in conditions:
        for c in (res.get("code", {}) or {}).get("coding", []) or []:
            code = str(c.get("code") or "")
            system = c.get("system") or ""
            if system == "http://snomed.info/sct" and code in snomed_codes:
                return True
            if system == "http://hl7.org/fhir/sid/icd-10-cm" and code.startswith(icd10_prefixes):
                return True
    return False


def _most_recent_observation(observations: list, loinc: str) -> dict | None:
    matches = []
    for res in observations:
        for c in (res.get("code", {}) or {}).get("coding", []) or []:
            if c.get("system") == "http://loinc.org" and c.get("code") == loinc:
                d = res.get("effectiveDateTime") or (res.get("effectivePeriod") or {}).get("start")
                vq = res.get("valueQuantity", {}) or {}
                matches.append({"date": d, "value": vq.get("value"), "unit": vq.get("unit")})
                break
    if not matches:
        return None
    return sorted(matches, key=lambda m: m["date"] or "", reverse=True)[0]


def _most_recent_procedure(procedures: list, cpt_codes: set[str]) -> dict | None:
    matches = []
    for res in procedures:
        for c in (res.get("code", {}) or {}).get("coding", []) or []:
            if c.get("system") == "http://www.ama-assn.org/go/cpt" and c.get("code") in cpt_codes:
                d = res.get("performedDateTime") or (res.get("performedPeriod") or {}).get("start")
                matches.append({"date": d, "cpt": c.get("code"), "label": c.get("display")})
                break
    if not matches:
        return None
    return sorted(matches, key=lambda m: m["date"] or "", reverse=True)[0]


def _months_since(record: dict | None) -> float:
    if not record or not record.get("date"):
        return float("inf")
    try:
        d = datetime.fromisoformat(record["date"].replace("Z", "+00:00"))
    except ValueError:
        return float("inf")
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - d
    return delta.days / 30.4375


# ── Rationale authoring (Gemini) ──────────────────────────────────────────────

_GEMINI_SYSTEM = (
    "You are a clinical care coordinator. Given a structured care-gap evidence "
    "dict, write ONE concise sentence (<=30 words) explaining to a clinician why "
    "closing this gap matters for THIS patient now. Reference the evidence directly. "
    "Do not invent facts. Do not add disclaimers."
)


def _author_rationale(gap: dict, age: int | None, gender: str) -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return _fallback_rationale(gap)

    try:
        # Lazy import — keep the MCP server bootable without google-genai installed.
        from google import genai

        client = genai.Client(api_key=api_key)
        prompt = (
            f"{_GEMINI_SYSTEM}\n\n"
            f"Patient age: {age}\n"
            f"Patient gender: {gender}\n"
            f"Gap title: {gap['title']}\n"
            f"USPSTF grade: {gap['uspstf_grade']}\n"
            f"Evidence: {gap['evidence']}\n\n"
            "Write the one-sentence rationale now."
        )
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt,
        )
        return (response.text or "").strip() or _fallback_rationale(gap)
    except Exception as e:
        return _fallback_rationale(gap, error=str(e))


def _fallback_rationale(gap: dict, error: str | None = None) -> str:
    suffix = f" (LLM unavailable: {error})" if error else ""
    return f"USPSTF Grade {gap['uspstf_grade']} screening overdue per evidence above.{suffix}"
