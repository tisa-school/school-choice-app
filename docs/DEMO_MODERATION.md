# Advisory AI-assisted Demo moderation

New and edited fictional activity submissions automatically receive a content-screening request. Listing content is disclosed at submission as being sent for advisory AI review. No child profiles, attendee records, parent requests, account identifiers, or real event records are sent. The endpoint never saves or publishes a real listing.

The server performs deterministic checks for missing title/description/accessibility/language/area/category/date-time information, risky wording, out-of-range or reversed ages, and age ranges in descriptions that disagree with the selected range. A keyword flag asks the admin to review its context; it does not accuse the organiser of wrongdoing. Instruction-like text cannot tell the moderation system to bypass its checks.

Claude adds contextual risky-word, missing-information and age-fit concerns, using validated structured output and the existing server-only `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL`. Local flags cannot be cleared by an AI response. A **Safe** label appears only after a valid completed AI result with no local or AI flags. Its visible explanation says no concerns were detected in the submitted text, not that real child safety, supervision, organiser identity or venue suitability is verified.

The admin always retains Approve and Reject. Neither a Safe label nor a Needs review label makes a publication decision. Unavailable keys/credits, provider errors, invalid output or request failures produce **Needs review** and a manual-review reason. A retry action is available for incomplete AI checks. All screening responses and reasons are plain data, never executable instructions or HTML.

Reports are tied to the exact submitted listing content and language. They survive refresh using the existing tab-scoped action checkpoint. Editing/resubmitting invalidates the report and starts a new check; late responses cannot replace a report for newer content or change a decided event. Only the new SCREEN_RESULT reducer action attaches advisory metadata, without altering listing status. Reset Demo clears these reports together with demo state.

The server reuses successful identical-content results for ten minutes; the browser deduplicates in-flight requests. CSRF, POST-only handling, bounded payload/output validation and existing rate limits apply. No new keys, dependencies or database migration are required. The feature is scoped to Demo moderation, not an assertion that production school content has undergone real safety assessment.

Tests cover clean AI results, risky-word overrides, missing fields, age conflicts, instruction-like text, provider failure, credential protection, extra private fields, no real publication, report persistence, stale-result rejection, edit-triggered rechecks, and independent admin approval/rejection. AI responses are mocked; no paid requests or real child data are used in tests.
