# Full-text Hungarian translation worker contract

Read only your assigned immutable `fulltext/jobs/<job>.json`. Write ONLY your assigned `fulltext/translations/<job>.json` and notes/chunk files beginning with the same job prefix in that directory. Other workers own other files. Do not touch originals, source jobs, builder, installed Windows app, release flags or other outputs. No recursive delegation or external paid API/CLI agents.

## Required deliverable
The final JSON is an array of `{ "unit_id": "<exact source ID>", "hu": "<complete Hungarian text>" }`, containing EVERY assigned unit exactly once. Do not truncate to a sample or summarize prose. Save intermediate numbered translation chunks frequently; attach the original long IDs programmatically using Python rather than retyping them. Read source in manageable batches.

## Meaning and safety
- Translate all patient-facing/anatomical text faithfully in fluent Hungarian. Preserve paragraphs, lists, negations, uncertainty qualifiers, sides, sex, organ/vessel/nerve class, numeric spinal levels, tooth numbering, numbers and units. Do not add treatment instructions, diagnoses or factual claims.
- Retain genuine anatomical Latin names/proper names. `draft_glossary.json` is a relevant-term lookup, NOT medical authority; do not dump the whole glossary into context. Original source/native-Latin data can itself be wrong.
- For definitions use conventional labels: Eredés, Tapadás, Beidegzés, Működés, Vérellátás. Preserve original Roman CN numbering and other identifiers.
- Do not silently repair source medical contradictions or guess the identity of an ambiguous mesh. Flag them with exact unit IDs in a separate `<job>-notes.json` file. Old patient information may be outdated; translate faithfully but flag suspect content, rather than presenting it as updated medical guidance.
- UTF-8 NFC, preserve literal `\\n`, placeholders, meaningful rich-text markup and numeric content. Do not leave English prose as a fallback. Legitimate unchanged Latin/proper names/acronyms can remain but must be noted.
- This is an AI translation draft, NOT medically qualified review or certification. Release remains blocked.

## Verify before final response
Use Python to check exact source ID set, uniqueness, nonempty NFC text and full coverage. Use the root `fulltext_tools.validate_unit` function on each source/target; report any formatting errors and numeric/negation flags, do not hide them. Do NOT alter validators to pass. Return actual counts, output path, notes and remaining risks. Do not falsely claim all inputs translated if you only saved partial chunks.
