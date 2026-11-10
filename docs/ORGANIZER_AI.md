# Fill with AI for organisers

The New activity editor in the demo and live organiser workspace now includes a one-sentence brief and **Fill with AI ✦**. Claude returns an editable English/European Portuguese draft covering title, description, age range, category, languages and accessibility.

Generated fields first appear in a review dialog. **Use draft fields** applies them to the existing form; **Keep editing manually** leaves all fields untouched. Applying never saves, submits, publishes or creates a listing. Existing manual edits remain available, and dates, times, prices, capacity, venues and contacts are never changed by AI. A later explicit draft save or staff-review submission remains necessary.

Ages, languages and accessibility need exact supporting excerpts from the organiser's sentence. Missing or ungrounded values are removed from the proposal and leave existing fields unchanged. The prompt prohibits invented access provisions, safety checks, supervision, qualifications and other unsupported factual claims. The organiser must still confirm all generated wording; evidence is not an independent accessibility assessment.

Only the typed sentence is sent to Claude. Account details, school records and private attendee/child data are not included. The shared server-only `ANTHROPIC_API_KEY` and optional `ANTHROPIC_MODEL` are reused. No new keys, dependencies or database migration are needed. Missing credits, missing keys, invalid output and provider failures preserve the original form and show a manual-entry fallback.

The live endpoint requires a verified organiser or verified school staff membership; the demo endpoint provides a fictional drafting experience without granting live publishing rights. Both require POST/CSRF and use the existing rate limits. The provider schema accepts only the supported fields and category/language enums; output is validated before display. Text is applied through native field values, not evaluated as HTML.

Tests cover structured extraction, no implicit writes, unsupported claims/values, missing credits, credential-safe errors, authentication/role checks, explicit review/apply, unchanged dates/prices, editable draft fields, failure recovery and subsequent draft-only saving. Provider responses are mocked in tests; no real API charges are incurred. Live Claude availability still depends on the owner's configured key and credits.

[Implemented AI draft review dialog](screenshots/organizer-ai-review.png), captured from the isolated browser test.
