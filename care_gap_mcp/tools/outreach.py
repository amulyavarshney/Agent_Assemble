"""Patient outreach drafter — turns a care gap into plain-language patient copy.

This is the second AI-factor tool: a rule engine can detect the gap, but only
an LLM can author warm, sixth-grade-reading-level outreach text that is
specific to this patient's evidence. We accept the gap object from FindCareGaps
and produce a short SMS-ready message plus a longer portal message.
"""
import os
from typing import Any

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
        drafts["sms"] = _generate(client, _sms_prompt(gap, patient_name))
    if channel in ("portal", "both"):
        drafts["portal"] = _generate(client, _portal_prompt(gap, patient_name))

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


_TONE = (
    "Sixth-grade reading level. Warm, not alarmist. Never use the word 'overdue' "
    "or 'gap' — phrase it as a recommendation. No medical disclaimers. No emojis. "
    "Do not invent specific dates, doctor names, or appointment slots."
)


def _sms_prompt(gap: dict, patient_name: str | None) -> str:
    name_phrase = f"Address them as {patient_name}." if patient_name else "Do not use a name placeholder."
    return (
        "Write a single SMS message under 160 characters inviting the patient to "
        "schedule. " + name_phrase + " " + _TONE + "\n\n"
        f"Care recommendation: {gap['title']}\n"
        f"Why it matters now: {gap.get('rationale', '')}\n"
        f"Evidence: {gap.get('evidence', {})}\n\n"
        "Output only the SMS text — no preamble."
    )


def _portal_prompt(gap: dict, patient_name: str | None) -> str:
    greeting = f"Hi {patient_name}," if patient_name else "Hi,"
    return (
        f"Write a patient-portal message starting with '{greeting}'. Three short "
        "paragraphs:\n"
        "1. What we're recommending (1-2 sentences).\n"
        "2. Why it matters for them, referencing the evidence specifically.\n"
        "3. Next step (call the clinic to schedule).\n\n"
        f"Tone: {_TONE}\n\n"
        f"Care recommendation: {gap['title']}\n"
        f"Clinical rationale: {gap.get('rationale', '')}\n"
        f"Evidence: {gap.get('evidence', {})}\n\n"
        "Output only the message body — no subject line, no preamble."
    )
