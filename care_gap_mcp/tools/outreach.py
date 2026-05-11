"""Patient outreach drafter — loads prompts from prompts/*.md.

Each LLM prompt is a separate markdown file under care_gap_mcp/prompts so the
clinical/comms team can edit tone, reading level, and structure without
touching Python. tone_guide.md is the shared style spec referenced by both
outreach_sms.md and outreach_portal.md.
"""
import os
from typing import Any

from po_fastmcp import load_prompt


def register(mcp) -> None:
    mcp.tool(name="DraftOutreachMessage")(draft_outreach_message)


async def draft_outreach_message(
    gap: dict[str, Any],
    patient_name: str | None = None,
    channel: str = "sms",
) -> dict:
    """Draft an outreach message for a care gap.

    Args:
        gap: A gap dict from FindCareGaps (id, title, severity, evidence, rationale).
        patient_name: Optional first name to personalize the message.
        channel: 'sms' (<=160 chars), 'portal' (3 short paragraphs), or 'both'.
    """
    if not isinstance(gap, dict) or "id" not in gap:
        return {"status": "error", "message": "gap argument must be the dict returned by FindCareGaps."}

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"status": "error", "message": "GOOGLE_API_KEY not set; cannot draft message."}

    try:
        from google import genai
    except ImportError:
        return {"status": "error", "message": "google-genai not installed."}

    client = genai.Client(api_key=api_key)

    drafts: dict[str, str] = {}
    if channel in ("sms", "both"):
        drafts["sms"] = _generate(client, _build_prompt("outreach_sms", gap, patient_name))
    if channel in ("portal", "both"):
        drafts["portal"] = _generate(client, _build_prompt("outreach_portal", gap, patient_name))

    return {
        "status": "success",
        "gap_id": gap["id"],
        "channel": channel,
        "drafts": drafts,
    }


def _generate(client, prompt: str) -> str:
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=prompt,
    )
    return (response.text or "").strip()


def _build_prompt(prompt_name: str, gap: dict, patient_name: str | None) -> str:
    """Compose <channel prompt> + <tone guide> + <gap evidence> into one string."""
    channel_prompt = load_prompt(prompt_name)
    tone_guide = load_prompt("tone_guide")
    name_line = (
        f"patient_name: {patient_name}" if patient_name
        else "patient_name: (not provided — open with a warm greeting only)"
    )
    return (
        f"{channel_prompt}\n\n"
        f"---\n# tone_guide.md (referenced above)\n{tone_guide}\n---\n\n"
        f"# Inputs for this draft\n"
        f"{name_line}\n"
        f"care_recommendation: {gap['title']}\n"
        f"clinical_rationale: {gap.get('rationale', '')}\n"
        f"evidence: {gap.get('evidence', {})}\n\n"
        f"Now write the message."
    )
