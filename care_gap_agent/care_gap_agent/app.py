"""
care_gap_agent — A2A application entry point.

    uvicorn care_gap_agent.app:a2a_app --host 0.0.0.0 --port 8001

Agent card published at:
    GET http://localhost:8001/.well-known/agent-card.json
"""
import os

from dotenv import load_dotenv

# Load .env BEFORE any module that reads env at import time (agent.py reads
# CARE_GAP_AGENT_MODEL; shared.middleware reads API_KEYS).
load_dotenv()

from a2a.types import AgentSkill
from shared.app_factory import create_a2a_app

from .agent import root_agent

_PORT = int(os.getenv("PORT", "8001"))
_PUBLIC_URL = os.getenv("CARE_GAP_AGENT_URL", os.getenv("BASE_URL", f"http://localhost:{_PORT}"))
_PO_BASE = os.getenv("PO_PLATFORM_BASE_URL", "https://app.promptopinion.ai")

a2a_app = create_a2a_app(
    agent=root_agent,
    name="care_gap_agent",
    description=(
        "Finds USPSTF-aligned preventive care gaps for the patient in context "
        "and drafts patient-facing outreach to close them."
    ),
    url=_PUBLIC_URL,
    port=_PORT,
    fhir_extension_uri=f"{_PO_BASE}/schemas/a2a/v1/fhir-context",
    fhir_scopes=[
        {"name": "patient/Patient.rs", "required": True},
        {"name": "patient/Condition.rs", "required": True},
        {"name": "patient/Observation.rs", "required": True},
        {"name": "patient/Procedure.rs", "required": True},
        {"name": "patient/MedicationRequest.rs"},
    ],
    skills=[
        AgentSkill(
            id="find-care-gaps",
            name="find-care-gaps",
            description=(
                "Identify open USPSTF preventive screening / monitoring gaps for "
                "the patient in context, with structured evidence and rationale."
            ),
            tags=["care-gaps", "uspstf", "fhir", "prevention"],
        ),
        AgentSkill(
            id="draft-outreach",
            name="draft-outreach",
            description=(
                "Draft patient-facing SMS or portal outreach copy for a specific "
                "care gap, written at a sixth-grade reading level."
            ),
            tags=["outreach", "communication", "patient-engagement"],
        ),
    ],
)
