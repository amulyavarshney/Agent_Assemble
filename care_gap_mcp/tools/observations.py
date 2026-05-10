"""Recent observations — labs and vitals, parsed for care-gap rule input."""
from datetime import datetime, timedelta, timezone

from po_fastmcp import FhirClient, get_fhir_context

LOINC_OF_INTEREST = {
    "4548-4": "HbA1c",
    "85354-9": "Blood pressure panel",
    "8480-6": "Systolic BP",
    "8462-4": "Diastolic BP",
    "2093-3": "Total cholesterol",
    "13457-7": "LDL",
    "2085-9": "HDL",
}

CPT_OF_INTEREST = {
    "45378": "Colonoscopy",
    "45330": "Sigmoidoscopy",
    "82270": "FIT (fecal immunochemical test)",
    "77067": "Mammography screening",
}


def register(mcp) -> None:
    @mcp.tool(name="ListRecentObservations")
    async def list_recent_observations(months_back: int = 24) -> dict:
        """Return observations + procedures from the last `months_back` months.

        Includes labs, vitals, and screening procedures (colonoscopy, mammography)
        relevant to the care-gap rules.
        """
        context = get_fhir_context()
        if context is None or not context.patient_id:
            return {"status": "error", "message": "FHIR context with patient_id is required."}

        cutoff = (datetime.now(timezone.utc) - timedelta(days=30 * months_back)).date().isoformat()
        client = FhirClient(context)

        obs_bundle = await client.search(
            "Observation",
            {"patient": context.patient_id, "date": f"ge{cutoff}"},
            limit=100,
        )
        proc_bundle = await client.search(
            "Procedure",
            {"patient": context.patient_id, "date": f"ge{cutoff}"},
            limit=50,
        )

        observations = [_summarize_observation(r) for r in obs_bundle]
        procedures = [_summarize_procedure(r) for r in proc_bundle]

        return {
            "status": "success",
            "patient_id": context.patient_id,
            "cutoff_date": cutoff,
            "observations": observations,
            "procedures": procedures,
        }


def _summarize_observation(res: dict) -> dict:
    code = res.get("code", {}) or {}
    codings = code.get("coding", []) or []
    loinc = next((c.get("code") for c in codings if c.get("system") == "http://loinc.org"), None)
    value, unit = None, None
    if "valueQuantity" in res:
        vq = res["valueQuantity"]
        value, unit = vq.get("value"), vq.get("unit") or vq.get("code")
    return {
        "loinc": loinc,
        "label": LOINC_OF_INTEREST.get(loinc) or code.get("text") or _first_display(codings),
        "value": value,
        "unit": unit,
        "effective_date": res.get("effectiveDateTime") or (res.get("effectivePeriod") or {}).get("start"),
    }


def _summarize_procedure(res: dict) -> dict:
    code = res.get("code", {}) or {}
    codings = code.get("coding", []) or []
    cpt = next((c.get("code") for c in codings if c.get("system") == "http://www.ama-assn.org/go/cpt"), None)
    return {
        "cpt": cpt,
        "label": CPT_OF_INTEREST.get(cpt) or code.get("text") or _first_display(codings),
        "performed_date": res.get("performedDateTime") or (res.get("performedPeriod") or {}).get("start"),
        "status": res.get("status"),
    }


def _first_display(codings: list) -> str:
    for c in codings:
        if c.get("display"):
            return str(c["display"])
    return "Unknown"
