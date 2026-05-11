# Patient SMS — Authoring Prompt

Write a single SMS message **under 160 characters** inviting the patient to
schedule a recommended care step.

## Personalization
- If a `patient_name` is provided, address the patient by first name.
- If not, do not use a name placeholder — open with a warm greeting.

## Tone & honesty
Follow every rule in `tone_guide.md`:
- Sixth-grade reading level.
- Warm, never alarmist.
- Never use the words "overdue", "gap", or "missing".
- No invented dates, doctor names, phone numbers, or slots.
- No medical disclaimers, no emojis, no markdown.

## Output
Output **only** the SMS text. No preamble, no quotation marks, no length
counter, no explanatory note.
