"""Patient summary tool — demographics + age computation from FHIR Patient."""
from datetime import date, datetime

from fhir.resources.patient import Patient

from po_fastmcp import FhirClient, get_fhir_context


def register(mcp) -> None:
    @mcp.tool(name="SummarizePatient")
    async def summarize_patient() -> dict:
        """Return demographics and computed age for the current patient.

        Returns a dict with keys: patient_id, name, gender, birth_date, age, status.
        Returns status="error" with a message when FHIR context is missing.
        """
        context = get_fhir_context()
        if context is None or not context.patient_id:
            return {"status": "error", "message": "FHIR context with patient_id is required."}

        resource = await FhirClient(context).read("Patient", context.patient_id)
        if resource is None:
            return {"status": "error", "message": f"Patient {context.patient_id} not found."}

        patient = Patient.model_validate(resource)
        name = _primary_name_text(patient)
        age = _compute_age(patient.birthDate) if patient.birthDate else None

        return {
            "status": "success",
            "patient_id": context.patient_id,
            "name": name,
            "gender": patient.gender,
            "birth_date": str(patient.birthDate) if patient.birthDate else None,
            "age": age,
        }


def _primary_name_text(patient: Patient) -> str:
    if not patient.name:
        return "Unknown"
    n = patient.name[0]
    if n.text:
        return str(n.text)
    given = " ".join(str(g) for g in (n.given or []))
    family = str(n.family) if n.family else ""
    return f"{given} {family}".strip() or "Unknown"


def _compute_age(birth_date) -> int:
    if isinstance(birth_date, str):
        birth_date = datetime.fromisoformat(birth_date).date()
    today = date.today()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )
