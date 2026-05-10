"""Active conditions / problem list."""
from po_fastmcp import FhirClient, get_fhir_context


def register(mcp) -> None:
    @mcp.tool(name="ListActiveConditions")
    async def list_active_conditions() -> dict:
        """Return the patient's active problem list with codings."""
        context = get_fhir_context()
        if context is None or not context.patient_id:
            return {"status": "error", "message": "FHIR context with patient_id is required."}

        bundle = await FhirClient(context).search(
            "Condition",
            {"patient": context.patient_id, "clinical-status": "active"},
            limit=50,
        )

        conditions = []
        for res in bundle:
            code = res.get("code", {}) or {}
            codings = code.get("coding", []) or []
            display = code.get("text") or _first_display(codings)
            conditions.append({
                "display": display,
                "snomed": _code_for_system(codings, "http://snomed.info/sct"),
                "icd10": _code_for_system(codings, "http://hl7.org/fhir/sid/icd-10-cm"),
                "onset": res.get("onsetDateTime") or (res.get("onsetPeriod") or {}).get("start"),
            })

        return {
            "status": "success",
            "patient_id": context.patient_id,
            "count": len(conditions),
            "conditions": conditions,
        }


def _first_display(codings: list) -> str:
    for c in codings:
        if c.get("display"):
            return str(c["display"])
    return "Unknown"


def _code_for_system(codings: list, system: str) -> str | None:
    for c in codings:
        if c.get("system") == system and c.get("code"):
            return str(c["code"])
    return None
