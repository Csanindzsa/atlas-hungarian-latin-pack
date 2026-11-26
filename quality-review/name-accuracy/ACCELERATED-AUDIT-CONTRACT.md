# Accelerated anatomical-name audit — authorized optimization

## REVISION 2 (supersedes lane assignments below)
- Ranks 1–300 are complete (run-01, run-02, run-03). The four earlier continuation lanes terminated with zero results; ignore fast-lane-03/, fast-lane-04/, run-02/continuation/, run-03/continuation/.
- Remaining ranks 301–2484 are split into ten lanes in LANES.json. Each lane writes ONLY quality-review/name-accuracy/<lane-id>/.
- Deterministic whole-catalog checks already ran over ALL 4643 rows: systematic/systematic-findings.json (Latin vs HU direction/type/side/size) and systematic/english-hu-findings.json (English vs HU). Only two genuine conflicts exist (keys 875 and 1951, both English-vs-Latin source conflicts); side suffixes are consistent everywhere. Lanes must NOT re-derive directions/sides/vessel class mechanically — treat a term with no systematic flag as having passed that mechanical check, and spend effort on the remaining question: is the Hungarian wording the standard Hungarian anatomical term for that structure?
- Outcome rubric (apply uniformly):
  - evidence-supported-with-scope-limits: the head noun and each qualifier use standard Hungarian anatomical vocabulary attested in a cited Hungarian academic source or TA2 equivalence, the composition follows normal Hungarian anatomical naming, and no systematic flag applies. A verbatim full-phrase citation is NOT required.
  - proposed-correction: a cited source shows a more standard or more accurate Hungarian term, or the current wording is wrong. Give exact current and proposed HU.
  - specialist-review-needed: ONLY for a concrete wording doubt (competing Hungarian conventions, possibly non-standard coinage, medialis/internus ambiguity that changes meaning within this dataset). State the specific doubt in one sentence. Do NOT use it merely because the full phrase is not printed verbatim.
  - unresolved-identity-model-evidence-needed: English/Latin/model identity genuinely conflict.
- Budget: aim for about 2–4 minutes of work per term family; save every 20 terms. Finish the whole lane.

The user asked why the audit is slow and whether it can be sped up. Use four disjoint lanes to keep the remaining CORE queue moving without waiting for parent acceptance after every100-term packet. This changes execution/reporting overhead, NOT medical truth or release criteria.

## Fixed ownership and assignments
- Base run-01 is immutable/read-only: canonical-queue.json, structure-occurrences.json, frozen input snapshots, already retrieved PDF/text sources and evidence ledgers.
- Existing run-02 worker: finish ranks101–200, THEN audit ranks1393–1938 in run-02/continuation/ without waiting for another parent/user message.
- Existing run-03 worker: finish ranks201–300, THEN audit ranks1939–2484 in run-03/continuation/ without waiting for another parent/user message.
- New fast-lane-03 owns ranks301–846 and writes only fast-lane-03/.
- New fast-lane-04 owns ranks847–1392 and writes only fast-lane-04/.
- All paths below quality-review/name-accuracy/. No recursive agents or paid API/CLI services. No master, original, installed-app, release-policy, other-lane or base-run edits.

## Remove avoidable work
1. Reuse the eight already retrieved reference PDFs/texts and source evidence. Root already live-verified their PDF hashes; do not repeatedly download the same books or copy1674 frozen inputs into each packet. Fetch new references only for genuinely uncovered topics.
2. Process manageable families/chunks internally. Save validated results every20–25 terms, with durable progress metadata, and continue through your ENTIRE assigned range. Keep context small with targeted table/text searches rather than dumping whole PDFs.
3. Review all assigned names and all associated row contexts. Reuse a documented terminology/direction/side rule across genuinely equivalent family members; a normal left/right or ordinal variation does not require its own literature search.
4. For ordinary compositional labels, exact source-attested anatomical components plus the correct standard Latin identity can support a clearly labeled compositional judgment. Do not demand that every routine inflected Hungarian phrase appear verbatim in a publication. Never extend this shortcut across different structures/types/organs or source conflicts.
5. Park genuine mesh/identity/source disagreements promptly, with exact IDs and a concrete reason. Do not spend the entire lane trying to solve an ambiguity unavailable evidence cannot settle. That is an UNRESOLVED disposition, not an accepted name.
6. Keep reports lean. Store a source quotation once, reference it from terms, and avoid repeating full original row records already in structure-occurrences.json. Row dispositions can contain occurrence_id, outcome and only context-specific notes; retain exact complete occurrence coverage. Use compact per-term reasons, not report-style essays.
7. No new inventory/report-generator framework per packet. The complete queue and frozen inventory already exist. Preserve current result schemas where convenient rather than wasting effort reformatting completed work.

## Non-negotiable quality
- No bulk fill of 'checked' from key/string equality, no fabricated citations, no model identity guessed from a Latin label. Inspect meaning, type, organ/region, direction, side, sex, level and Hungarian terminology for every assigned term.
- Shared class-neutral adjectives/headings can be supported only with explicit limits; they are not automatically accurate standalone artery/vein/nerve names. Preserve unresolved class/mesh questions.
- A lexical/cited component match is NOT full anatomical or clinical certification. Preserve exact native IDs, markers, Latin, suffixes and answer/program data. No deployment or gate changes.
- Propose actual corrections when evidence supports them; include exact current/proposed HU and relevant citation. Do not merely copy an old specialist flag, and do not manufacture a clean outcome when no evidence exists.
- Record one explicit outcome per term and every occurrence: evidence-supported-with-scope-limits; proposed-correction; specialist-review-needed; unresolved-identity-model-evidence-needed. Cite genuine relevant sources for support/corrections. Missing references are unresolved, not silently accepted.
- Validate exact rank/key set, uniqueness, unchanged final HU inputs, every associated row occurrence and literal quoted evidence before final delivery. Save partials so interruption does not lose work.

## Deliverables
- Existing workers retain their originally assigned100-term output. Continuations and new lanes save chunk results plus aggregate results.json, evidence references/quotes and compact validation/progress JSON.
- Preserve clear distinction between completed dispositions, unresolved holds and unreviewed terms. All supplementary catalog/prose/UI name queues remain separate; core coverage does not automatically clear them.
- Parent independently validates finished output and approves any data corrections. Release, medically qualified review and actual in-app rendering remain separate blocked gates.
