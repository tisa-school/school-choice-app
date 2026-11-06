# TK-Zone — Tech Week presentation release

## Scope and preservation

This release extends **tisa-school/school-choice-app**, the Django application in this workspace. It does not use or depend on the separate Next.js repository. Existing authentication, school boundaries, PostgreSQL models, private uploads, real parent/organiser workflows, staff ticket approvals, notifications, saved-data receipts, and community feedback remain in place. No production database changes or new migrations are required.

The latest supplied specification overrides the earlier branch name and credits: development uses `feature/tk-zone-final-polish`; school branding is Unicorn School; Artem Tolmachev is included in school leadership. The latest pasted specification was read fully. Separate files named AGENTS.md and FINAL_PROMPT.md were not supplied. No student biographies, photos, achievements, numerical survey findings, partnerships, or endorsements are invented. Zehra Yilmaz is credited once per About page, with both project lead and STEAM mentor responsibilities.

## Implemented presentation

`/demo/` is a single-document browser presentation served by Django. Navigation uses History API and delegated links, so role changes preserve the current session. All demo actions use the pure reducer in `static/community/demo-state.js`; the UI uses `demo.js`. No fetch, real API, external AI, localStorage, sessionStorage, email, or database mutation is used. The demo response includes CSP `connect-src 'none'` and `form-action 'none'`. Reload clears the session. Real application routes remain separate and retain their existing protections.

Included journeys:

- Mission landing and fictional Anna/Emma onboarding, with a visual four-digit PIN that is validated but never stored.
- Emma's dashboard, interests, recommendations, saved activities, upcoming requests, exploration progress, and Portuguese word of the day.
- Ten deterministic fictional Lisbon events/activities with category SVG illustrations, bilingual titles/descriptions, varied ages, areas, languages and prices.
- Search plus age, interest, area, language and price filters, combinations, active removable chips, clear-all, weekend selection, counts and empty states.
- Details with factual rule-based match explanations, accessibility notes, fictional organiser attribution, simulated-review disclaimer, save, report and parent permission.
- Duplicate-resistant permission requests; Anna's approvals/declines; conflict detection; cancellation of permissions; approved and cancelled plans retained in the family calendar.
- Four Crews with parent permission requests, capacity up to eight, planned activity concepts, and group guidelines; no messages or identifying rosters.
- Organiser create/edit/draft/preview/review submission; admin review, simulated organiser decisions, reports, synthetic statistics and audit history. Submitted/edited events require new review before discovery.
- Organiser/admin-only simulated cancellation with ownership and reason validation, modal confirmation, idempotent updates to pending/approved requests, fictional notification, and retained cancelled calendar entries.
- Safety Centre and About with exact owner-supplied team credits. No real-world verification or legal certification claims.
- In-memory English/European Portuguese switching across all essential demo content. Existing production English/Portuguese/Turkish catalogs remain available separately.
- Presenter guide, quick roles, repeatable seeds and confirmed reset.

The demo uses new scoped CSS with the requested violet/dark-violet/light-violet/orange/peach/ink palette. Archivo, DM Mono, and Source Serif 4 are hosted locally with their OFL licenses. Shared production tokens and typography follow the prospectus palette while preserving existing layouts and functionality. Orange is limited to small decoration; peach provides text on violet surfaces.

## Succession animation

`succession.js` and `succession.css` provide a shared progressive enhancement utility. Selected content groups enter with scale .96 to 1, opacity 0 to 1, and a 3px blur to sharp, over 560ms; at most four groups are observed per view. The observer starts an animation only when content approaches the viewport, and the underlying content is visible by default. It disconnects on navigation/pagehide and honours reduced-motion changes immediately. There is no permanently hidden pre-animation state.

Applied selectively to demo hero/illustration/benefits, page headings, child/parent overview groups, Crew introduction, admin/organiser summaries, Safety Centre principles, and About mission/team. Existing About, discovery, home, family, organiser, staff and studio templates receive selected reveals through the same utility. Forms, controls, alerts and decisions are not animated. Filter changes, language switches and state updates render immediately without entrance replay.

## Verification

Executed validation:

- 134 Django backend tests passed on isolated PostgreSQL.
- Existing student/staff, family and organiser Chromium workflows passed as part of the regression run.
- Dedicated final-demo Chromium tests cover the guided presentation, five combined filters, saving, approval/decline, Crew permissions, submission/moderation/reporting/cancellation, reset, bilingual navigation, keyboard use, exact credits, and 360/390/768/1024/1440px layouts.
- The demo interaction browser test records no network requests after initialization and no real Event records.
- Nine pure JavaScript reducer tests passed with `node static/community/demo-state.test.cjs`.
- Django checks, migration drift checks, JavaScript syntax checks, and the actual Vercel preview build script passed locally. Required production settings still fail closed when missing. There is no TypeScript project to type-check; no Next.js build was introduced.

Commands:

```sh
python manage.py collectstatic --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test community.tests community.test_features community.test_migrations community.test_persistence community.test_organizers community.test_demo community.test_release_a --noinput
node static/community/demo-state.test.cjs
node --check static/community/demo.js
node --check static/community/demo-state.js
node --check static/community/succession.js
# Requires requirements-dev.txt and Chromium at /usr/bin/chromium:
python manage.py test community.browser_tests community.browser_demo_final --noinput
```

The initial full regression run found one obsolete homepage copy assertion; the fallback now includes discovery copy, and that test plus the demo endpoint suite passed on rerun. PostgreSQL subsequently passed the entire backend suite. Earlier browser failures found a missing content fallback, ambiguous selectors and retained-filter test assumptions; these were corrected before the passing checks. No failed check is represented as a pass.

## Two-minute presenter guide

1. **0:00–0:15** Open `/demo/`. Say: “Find your crew. Explore your city. Feel at home.” Press **Present Demo**.
2. **0:15–0:30** Next: meet Emma, 11, new to Lisbon, interested in art, science and mathematics.
3. **0:30–0:45** Next: show the five combined art filters and one matching activity.
4. **0:45–1:00** Next: open Creative Art Afternoon. Explain the age/interest/language match and simulated review label.
5. **1:00–1:15** Ask mum or dad. Next, then Next to reach Anna's inbox. Approve the request.
6. **1:15–1:35** Next: show the approved plan in the family calendar. Clarify that this is not a real booking.
7. **1:35–1:50** Next: introduce Crews and parent-controlled joining, without private messaging.
8. **1:50–2:00** Next: close with the mission. Use Reset Demo and confirm before the next rehearsal.

Use in-app links and role switching during the presentation. A page reload intentionally resets in-memory state. For a projector, use a 1440px desktop viewport or wider. All seed dates are fixed in November 2026; they are fictional examples, not a live event feed.

## Screenshots

Captured from the real implemented Chromium interface, with fictional data:

- [Discover](screenshots/discover.png)
- [Event Detail](screenshots/event-detail.png)
- [Parent Inbox](screenshots/parent-inbox.png)
- [Mobile Event Detail](screenshots/event-detail-mobile.png)

## Deployment boundary and remaining steps

Only the feature branch is intended for push. Main, production settings and production data are unchanged. GitHub CLI pull-request access returned `Forbidden` from `api.github.com/graphql`; no PR or preview readiness can be claimed from that response. No Vercel credentials are connected, and the environment proxy blocks Vercel host access. A local successful build is not proof of a hosted deployment.

Once the feature branch is pushed, open a PR through the repository's compare page, check its Vercel Preview build, and rehearse the essential journey there. Merge/deploy to production requires the owner's explicit approval. The supplied separate Next.js URL is not used as proof of this Django application's preview. Human Portuguese editorial review and a real-device/projector rehearsal are recommended before 12 November. No real-world safeguarding verification, booking, authentication, GDPR certification, or AI service is added to the demo.

## Changed files

- `.github/workflows/checks.yml`
- `README.md`
- `community/browser_demo_final.py`
- `community/browser_tests.py`
- `community/demo.py`
- `community/test_demo.py`
- `community/test_release_a.py`
- `config/urls.py`
- `content/about.json`
- `content/locales/en.json`
- `content/locales/pt-PT.json`
- `content/locales/tr.json`
- `content/project.json`
- `docs/TECH_WEEK_FINAL.md`
- `docs/WEB_SUMMIT_RELEASE_A.md`
- `static/community/demo-final.css`
- `static/community/demo-state.js`
- `static/community/demo-state.test.cjs`
- `static/community/demo.js`
- `static/community/succession.css`
- `static/community/succession.js`
- `templates/base.html`
- `templates/community/about.html`
- `templates/community/demo.html`
- `templates/community/discover.html`
- `templates/community/family.html`
- `templates/community/home.html`
- `templates/community/organizer.html`
- `templates/community/staff.html`
- `templates/community/studio.html`

Screenshot files are listed above.

## Prospectus and deployment follow-up

The owner subsequently requested deployment to Vercel and confirmed the exact prospectus palette and Archivo / DM Mono / Source Serif 4 fonts. All three fonts are now bundled with their OFL licenses; shared site tokens and presentation typography have been updated. All eight Chromium production/demo workflows passed after this change, including the bilingual viewport matrix. The real Vercel preview build script passed locally again. The owner's follow-up authorizes advancing main for the connected GitHub-to-Vercel pipeline; hosted deployment readiness remains subject to verification in Vercel.
