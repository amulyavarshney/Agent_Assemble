# Patient Portal Message — Authoring Prompt

Write a patient-portal message in **exactly three short paragraphs**:

1. **What we're recommending** — one or two sentences. Direct, friendly.
2. **Why it matters for them** — reference the evidence specifically (their
   age, the time since their last screening, the diagnosis on their record).
   Keep it concrete; avoid generic statements about "preventive care".
3. **Next step** — invite them to call the clinic to schedule.

## Greeting
- If a `patient_name` is provided, open with `Hi <name>,`
- Otherwise, open with `Hi,`

## Tone & honesty
Follow every rule in `tone_guide.md`:
- Sixth-grade reading level.
- Warm, never alarmist.
- Never use the words "overdue", "gap", or "missing".
- No invented dates, doctor names, phone numbers, or slots.
- No medical disclaimers, no emojis, no markdown.

## Output
Output **only** the message body. No subject line, no preamble, no
explanatory note.
