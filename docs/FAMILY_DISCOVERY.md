# Family discovery and school directory

The existing Django app now opens a family discovery homepage. Production events, staff moderation, tickets, organisers, parent permissions, and the separate fictional `/demo/` presentation remain in place.

## Routes and behaviour

- `/`: new homepage, interest links, age/interest chooser, sourced school entry point. Weekend cards appear only when upcoming published listings exist.
- `/discover/activities/`: combined one-off events and recurring activities; keyword, age, dates, category, neighbourhood, price, setting, and language filters. Recurring activities use their next eligible uncancelled session. Surprise me chooses only from current matches. Return links preserve filters.
- `/schools/`: school-specific search, school type, age, stage, teaching language, curriculum, and published starting annual-fee filters.
- `/schools/<slug>/`: practical school facts, source/date, and explicit missing information. External links appear only when supplied.
- `/schools/compare/`: at most three published profiles, consistent comparison fields, no ranks or invented scores. Fee comparisons include coverage and academic year.
- `/saved/`: separate activities and school shortlist. Guests save public IDs on their device with localStorage; account holders use owner-scoped database records. Existing account collections remain available. Comparison selection stays on the device. Clearing browser storage clears guest lists.
- `/staff/school-profile/`: verified school staff can maintain only their own linked school profile. Superusers can maintain other directory records in Django admin. Publishing requires a source and last-checked date; quoted annual fees need a year and coverage.

## Data and preservation

Migrations `0013` and `0014` are additive. Existing events gain an optional external booking URL; no existing content is deleted or made public. Public directory records are separate from private school memberships and invite codes.

The only initial school profile is Unicorn School, with the name, Lisbon location, and relationship to this project supplied by the school presentation. It explicitly says no independent website check was performed. Its teaching languages, curriculum, ages, fees, admissions, and facilities are unknown, not inferred. Additional school profiles need reliable sources; this is not a complete Lisbon directory. No real events or school records are fabricated for demonstration. Automated tests use isolated fictional fixtures.

Activity covers retain the existing reviewed, subject-specific imagery and illustrative disclosure. The home hero is clearly labelled as an AI activity illustration, not an actual event. Uploaded organiser imagery still follows the existing image review policy.

Core new interface copy is translated into European Portuguese. Other existing locales retain their available translations and English fallback for new copy. School-authored information retains its source wording.

## Deployment and checks

The existing Vercel build script applies migrations in Production only; Preview builds do not migrate a production database. Production needs its existing PostgreSQL/environment settings. No new paid API or key is required for discovery, saving, or comparison.

Automated coverage includes combined filters, recurring dates, visibility, duplicate saves, school ownership, source validation, comparison limits, filter-preserving navigation, mobile hero placement, device persistence, and school shortlist interactions. Run the normal backend suite and the additional browser module `community.browser_family_discovery`.

### Verification for this change

- Django backend suite: 260 passed; final targeted source/save/back-link checks: 11 passed.
- Chromium regression suite: 32 passed across the existing presentation and new discovery workflows; final discovery rerun: 2 passed.
- Node suites: 30 passed; syntax checks passed for demo and discovery-saves scripts.
- Django system checks and migration drift checks passed.
- Actual `scripts/vercel-build.sh` passed with Vercel Preview settings and an isolated nonconnecting PostgreSQL URL. This checks packaging, not live production migration or hosted deployment readiness.

Screenshots in `docs/screenshots/family-discovery-home-{desktop,mobile}.png` show the implemented homepage. `family-school-comparison-test.png` uses isolated browser-test schools to demonstrate comparison; these are not production directory entries.
