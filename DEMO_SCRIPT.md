# 3-Minute Demo Script

A tight script for the under-3-minute demo video required by the hackathon.
Times are cumulative.

## 0:00–0:20 — The problem (15s + 5s buffer)

> "Healthcare AI demos always show a chatbot answering a clinical question.
> The boring truth is that 80% of preventive-care work isn't *finding* the
> gap — it's writing the *follow-up* to close it. That's where Gemini earns
> its keep."

Visual: split screen — left side shows a HEDIS/Star-Ratings dashboard with
red 'overdue' tiles; right side shows an empty patient outreach inbox.

## 0:20–0:50 — The architecture (30s)

> "I built two things for Prompt Opinion: an MCP server that finds care gaps,
> and an A2A agent that uses it. The MCP server speaks SHARP-on-MCP — FHIR
> context arrives as headers. The agent speaks A2A v1 with the Prompt Opinion
> FHIR-context extension. Both register into the PO marketplace and run on
> my laptop through ngrok."

Visual: the architecture diagram from the README — show patient → PO portal
→ A2A agent (via ngrok) → MCP server (via ngrok) → SMART FHIR sandbox.

## 0:50–1:50 — The live demo (60s)

In the PO portal, open patient Danae Kshlerin (the Synthea patient with
diabetes, age 61, no recent A1c).

Type: **"What preventive care gaps does this patient have?"**

The agent:
1. Calls `summarize_patient` → confirms Danae, 61F.
2. Calls `find_care_gaps` → rule engine returns 3 gaps; Gemini authors a
   one-sentence rationale per gap.
3. Renders a clean bulleted summary:
   - **HbA1c overdue** — last A1c was 5.5 years ago in November 2020.
     Gemini rationale: "Patient has long-standing type 2 diabetes; an A1c
     after 5+ years without monitoring puts her at high risk for unrecognized
     glycemic deterioration."
   - **Colorectal screening overdue** — no record on file.
   - **Mammography overdue** — no record on file.

Visual: emphasize that the rule engine *finds* the gaps; the LLM only writes
the rationale. Highlight the structured `evidence` block in the JSON.

## 1:50–2:30 — The "what software can't do" moment (40s)

Type: **"Draft an SMS to Danae about the A1c."**

The agent calls `draft_outreach_message` with the gap object. Gemini writes:

> "Hi Danae — your last A1c blood test was a while back. A quick check-in
> helps us keep your diabetes on track. Call us at the clinic when you can,
> and we'll find a time that works."

> "A rule engine could have told you Danae was overdue. It could not have
> written that. The hard part of preventive care isn't detection — it's
> authorship. That's the AI factor."

Visual: split screen — left side shows the structured FHIR data, right side
shows the rendered SMS. Show the character count is under 160.

## 2:30–2:55 — Standards & feasibility (25s)

> "Three things judges asked about: privacy, feasibility, real-world fit.
> Patient FHIR tokens never enter an LLM prompt — they live in headers and
> session state. SHARP scopes are declared on the MCP capability and the
> A2A agent card. Every gap is grounded in a specific SNOMED, LOINC, or CPT
> code; the LLM only authors copy. This drops into any SMART-on-FHIR EHR
> that PO already bridges."

Visual: brief flash of the agent card JSON showing
`apiKeySecurityScheme` and the FHIR extension's `params.scopes`.

## 2:55–3:00 — Close (5s)

> "Care Gap Closer. Built for Agents Assemble. Code at github.com/<you>/care-gap-closer."
