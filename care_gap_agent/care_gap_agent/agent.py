"""
care_gap_agent — A2A agent for USPSTF preventive care gap workflows.

The agent has no FHIR tools of its own; it delegates ALL data access and
content authorship to the Care Gap Closer MCP server. The agent's job is the
multi-turn reasoning: figuring out which tool to call, threading evidence
between tools, and surfacing the right summary to the user.

Tool flow (typical):
    summarize_patient → find_care_gaps → draft_outreach_message(gap=...)
"""
import os

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from shared.fhir_hook import extract_fhir_context
from shared.tools import (
    draft_outreach_message,
    find_care_gaps,
    list_active_conditions,
    list_recent_observations,
    summarize_patient,
)

_model_name = os.getenv("CARE_GAP_AGENT_MODEL", "gemini/gemini-2.5-flash")
_model = LiteLlm(model=_model_name)

root_agent = Agent(
    name="care_gap_agent",
    model=_model,
    description=(
        "Identifies USPSTF-aligned preventive care gaps for the patient in "
        "context and drafts patient-facing outreach to close them. Calls the "
        "Care Gap Closer MCP server for all FHIR access and content drafting."
    ),
    instruction=(
        "You are a care coordinator working alongside a clinician. "
        "Your job is to find preventive-care gaps for the patient currently "
        "in context and help the clinician decide how to close them. "
        "\n\n"
        "Workflow you should follow when asked about care gaps:\n"
        "1. Call summarize_patient to confirm who you're working with.\n"
        "2. Call find_care_gaps — this returns a structured list of gaps "
        "with evidence and a one-sentence rationale per gap.\n"
        "3. Present the gaps to the clinician concisely (title + rationale "
        "+ key evidence numbers like the months-since-last-screening). "
        "Do NOT just dump the JSON. Use a short bulleted summary.\n"
        "4. If the clinician asks to reach out to the patient about a "
        "specific gap, call draft_outreach_message with the FULL gap object "
        "from step 2 (not just the id) and the patient's first name.\n"
        "\n"
        "Use list_active_conditions or list_recent_observations only when "
        "the clinician asks for the underlying data directly.\n"
        "\n"
        "Never invent FHIR data. Never invent care gaps — only report what "
        "find_care_gaps returns. If FHIR context is missing, say so plainly "
        "and ask the caller to include fhir-context in the message metadata."
    ),
    tools=[
        summarize_patient,
        list_active_conditions,
        list_recent_observations,
        find_care_gaps,
        draft_outreach_message,
    ],
    before_model_callback=extract_fhir_context,
)
