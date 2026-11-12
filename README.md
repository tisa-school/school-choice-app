# TK-ZONE ✦

A working, school-scoped events and community application. Django 5.2 LTS, Python 3.12+, SQLite, server-rendered semantic HTML, and progressive JavaScript. The six brand colors are shared CSS variables; Archivo Black and Inter are hosted locally under their included OFL licenses. No external frontend runtime, invented events, default accounts, invite codes, or statistics.

## TK-ZONE 2.0 upgrade

See [implementation evidence, limitations and safe deployment steps](docs/PLATFORM_V2_RELEASE.md) for the five-section discovery platform, private family calendar, four-school comparison, consolidated product tour and scoped administrator workspace. New research targets remain unpublished until checked against official sources.

## Vercel + GitHub

See [the deployment guide](docs/VERCEL.md) for the `tisa9` team. PostgreSQL persistence, private database-backed images, static assets, production migrations, and GitHub checks are configured. Connecting the GitHub App and supplying production service credentials in Vercel are separate from this local setup.

## Develop

```sh
cd /workspace/school-choice-app
python -m venv /workspace/tkzone-venv
/workspace/tkzone-venv/bin/pip install -r requirements.txt
/workspace/tkzone-venv/bin/python manage.py migrate
/workspace/tkzone-venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload
```

In a second process, start scheduled publication:

```sh
cd /workspace/school-choice-app
/workspace/tkzone-venv/bin/python manage.py publish_scheduled --watch
```

The scheduler publishes due announcements every 30 seconds and creates inbox notifications exactly once. Due announcements are also processed when a school member visits. In production use a supervised worker or run `publish_scheduled` from a minute scheduler.

The existing isolated checkout is the development workspace. Do not create another worktree unless explicitly requested.

## Connect a real school

There is deliberately no sample content in the application database. Students can register immediately, but school content requires a school configured by a trusted operator. Email verification is currently disabled; private school codes gate membership. Registration never grants staff privileges.

1. The school contact registers using **Create account**. Use their real name and email. No account is created automatically from an email supplied in a chat.
2. A trusted environment operator creates the school:

   ```sh
   /workspace/tkzone-venv/bin/python manage.py configure_school --name 'Your actual school' --timezone Europe/Lisbon --staff-email '<registered staff email>'
   ```

   The command securely prompts for an invite code of at least 12 characters, stores only its password hash, and verifies the existing contact as school staff. It does not print the code. Share it with students privately.
3. Students register, search for the school, and join with that code. Accounts have one school membership. Staff create real events and announcements from their staff workspace.
4. To verify another registered staff account, a trusted operator runs:

   ```sh
   /workspace/tkzone-venv/bin/python manage.py grant_staff --school-id <id> --email '<registered staff email>'
   ```

For membership auditing or changes, create a trusted Django superuser with `manage.py createsuperuser`; the protected `/admin/` is separate from the school workspace. Regular school staff do not receive Django admin privileges.

## Functionality

- Password signup/login, visibility toggles, authenticated password changes, generic password recovery responses, secure cookie sessions, CSRF protection, and database-backed per-address/per-route POST limits (30 / 10 minutes).
- School-code membership, server-side school and verified-staff checks on every private action, protected image responses, safe rendered text, and validated raster uploads up to 5 MB / 24 megapixels.
- Upcoming events, title/body/venue search, categories, school-time-zone calendar, event details, four-stage staff editor, drafts, image upload, capacity and request deadline configuration. Unknown price is exactly **Price on request**. No payments.
- Confirmed ticket request submission, duplicate-active-request constraint, request history, review/approval/decline, staff notes, cancellations, accurate wallet and inbox notifications. Pending requests never imply admission.
- SQLite `IMMEDIATE` transactions serialize writers. Approval and capacity edits happen inside those transactions; concurrent approvals cannot exceed capacity. `select_for_update` is also used around the event and request. Switching database engines requires reviewing and testing their locking strategy.
- Persistent saved events, collection creation/rename/covers/add/remove/delete, pinned announcements, draft/preview/publish/unpublish/scheduling, private notifications and read state, profile name editing, local-device larger-text and reduced-motion preferences.
- Responsive navigation, keyboard focus, native accessible confirmation dialogs, semantic labels, reduced-motion CSS, empty and error states. Avatar uses the user's initial, with no external avatar service.

## Checks

```sh
/workspace/tkzone-venv/bin/python manage.py check
/workspace/tkzone-venv/bin/python manage.py test --noinput
```

The suite includes separate connections racing for a one-seat event. It uses an isolated file-backed test database, destroyed after each run. Browser tests use isolated fictional test data, never live application records:

```sh
/workspace/tkzone-venv/bin/pip install -r requirements-dev.txt
# Chromium is available at /usr/bin/chromium in this cloud environment.
/workspace/tkzone-venv/bin/python manage.py test community.browser_tests --noinput
```

The browser test covers staff event creation, student registration and membership, mobile search, save, ticket request dialog, staff approval, student wallet, collections, announcement preview/publication, inbox, preferences, and three viewport sizes. Screenshots are written to `/tmp/tkzone-mobile.png` and `/tmp/tkzone-desktop.png` using isolated test content.

## Local data and recovery email

`db.sqlite3`, `.local-secret`, `private-media/`, and `local-mail/` are ignored local state. Keep these private; database and uploads persist across server restarts. Back up the database and media together. The development secret is generated once and stored with mode 0600. Do not publish local state to Git.

Recovery email defaults to a private file backend in `local-mail/`, so local development needs no SMTP credentials and sends no email. Those files contain sensitive recovery links: never commit or share them. For real email delivery configure `DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL` securely on the deployment platform. SMTP requires actual transport credentials, rather than a proxy-only HTTPS credential placeholder. In-app notifications do not require email delivery.

## Deployment boundary

This is a runnable development environment, not a published production deployment. Before production:

- Set `DJANGO_DEBUG=0`, a securely generated `DJANGO_SECRET_KEY`, the actual `DJANGO_ALLOWED_HOSTS` (comma separated), and `DJANGO_CSRF_TRUSTED_ORIGINS` (comma-separated HTTPS origins). Production refuses to start without the secret. Secure cookies, SSL redirect, and HSTS are enabled in production mode.
- Serve HTTPS with a proper WSGI server; do not deploy Django's development server. Explicitly configure any trusted reverse proxy; do not blindly trust forwarded headers.
- Run migrations and `collectstatic`, serve `staticfiles/` through the web server, and keep `private-media/` accessible only through authenticated Django routes. Configure request body limits and durable private storage/backups.
- Run the scheduled publication worker, configure SMTP for real password recovery, and run `manage.py check --deploy` with the production settings.
- SQLite is appropriate for this single-instance school workflow. Use durable local storage and a supervised single deployment; horizontal scaling requires a reviewed database and storage configuration. Reinforce authentication rate limits at the trusted ingress when deployed behind a reverse proxy.

No email, payment, production publishing, or outbound messaging has been performed by setup.

## Public discovery and family features

The homepage, Events, Activities, Activity Finder, and approved public details now open without login. **Existing listings stay school-only** after the additive migration. To make a listing public, verified school staff select Public and Published in the listing editor. Publication records the reviewing account and time. Drafts and organizer submissions are never public. Public images follow the same listing-visibility policy; school announcements stay private.

Events are one-off occasions. Activities have individually scheduled sessions, each with separate capacity and requests. Staff create a listing, choose Activity, then add sessions from its edit page. Session cancellation also cancels its active family requests and creates private inbox notifications. Editing capacity cannot reduce it below already allocated places.

Guests can browse by age, interest, language, area, date, price, and audience. Filters remain in the URL. Missing age/language information is not treated as a positive match. A recurring session is filtered by its actual local date, using the listing's IANA time zone. Numeric prices are in EUR; no payment is collected, and absent prices remain **Price on request**.

Parents register through the Parent account action, explicitly declare they are an adult guardian, and create private child profiles with nickname, age band, interests, and language codes. This declaration is not identity verification. Existing school student accounts cannot promote themselves to parents; guardians need their own accounts. A parent may join a school using the private school code to see school-only listings.

The family workflow is **Interested → Awaiting parent approval → Awaiting organizer confirmation → Confirmed**, with declined and cancelled states. Parent approval requires the parent's current password. Interest and parent approval do not reserve places. Verified staff confirm places in the existing approval center. Confirmations share transactional event capacity with legacy school tickets, and activity sessions have independent allocations. Legacy student tickets and their history are preserved rather than inventing parent-child relationships for old accounts.

The Family workspace includes saved plans, a calendar agenda, private calendar export, child profile editing/deletion, participation history, and review actions. Adding a family plan never makes a booking. Named saved collections work for accounts without school membership too. Child profiles are not public; staff see only the nickname and age band needed to review requests.

Trusted administrators can grant external submitters an **Organizer** membership through Django admin. Organizers can edit their own submissions, but every submission or edit is held for staff review; they cannot publish or claim identity verification. Staff alone record organizer identity checks, which are described separately from safety assurances.

### Optional AI Activity Finder

Set `ANTHROPIC_API_KEY` as a Secret in Vercel → Project Settings → Environment Variables → Production (and Preview if needed), then redeploy. The server calls Claude Messages with a forced filter-extraction tool. `ANTHROPIC_MODEL` optionally overrides the default `claude-haiku-4-5-20251001`. Never put a key in source, browser code, or chat. No new package or paid resource is provisioned by this change. A real provider key and its usage terms are prerequisites for live AI requests; none is bundled in the source.

Only the visitor's explicitly submitted preference sentence is sent to `https://api.anthropic.com/v1/messages`, after they confirm it contains no private information. Stored child profiles, account details, and listing descriptions are never sent. The model outputs validated search filters, not listings or booking actions. Database filters enforce visibility, ages, language, date, price, and remaining capacity. Recommendation explanations and missing-information notes are built from actual database fields and link to source listings. No listings or availability are generated. Provider errors fail to an explanatory standard-search fallback without exposing credentials or provider response bodies.

Without a key, the app explicitly says AI is not configured and keeps all ordinary discovery filters working. No fake AI response or automatic participation action is used.

### Feature validation

```sh
/workspace/tkzone-venv/bin/python manage.py test community.tests community.test_features community.test_migrations --noinput
/workspace/tkzone-venv/bin/python manage.py test community.browser_tests --noinput
```

The backend tests run on SQLite and PostgreSQL; GitHub CI includes the new-feature suite. Browser tests cover both the retained student ticket workflow and the public-home → parent account → activity session → guardian approval → organizer confirmation workflow at mobile, tablet, and desktop widths. Test-only records never enter the live database.

Pushes to the connected GitHub `main` branch trigger Vercel deployments. The existing production build applies the additive migration automatically. No required deployment variables have changed; the AI key is optional. Actual hosted deployment status must be checked separately from local build success. SMTP is still required for real password-reset delivery if the current deployment uses the dummy email backend.

## Saved-data status

Signed-in users see their last server-confirmed save and its timestamp in the expandable **Saved to database** banner. Each user's receipt is private and persists in PostgreSQL. The banner describes the last completed application save, not unsaved edits or device-only preferences.

Write forms show **Unsaved changes** while editing and **Saving to database…** after valid submission. Server validation errors show **Not saved**; unsuccessful writes do not replace the previous receipt. Save receipts participate in the transaction when the underlying write is transactional. Returning to a stale page does not claim an unconfirmed submission succeeded. Authentication, AI searches, and device-only accessibility preferences are excluded from this database-save feedback.

No Gmail integration or email delivery is needed for this feature. Existing email-backend settings are unchanged. The additive `0004_savereceipt` migration runs during the Vercel production build. `community.test_persistence` verifies successful writes, rejected forms, receipt privacy, persistent timestamps, and rollback behavior; browser tests check the visible save feedback.

## Organizer event studio

Organizers now have a dedicated studio at `/organizer/` with real draft, review, published, and confirmed-place counts. Adults without access can apply at `/organizer/apply/`; the selected school's verified staff review applications at `/staff/organizers/`. Approval grants organizer posting access only, not access to other school-private listings or internal announcements, and not automatic identity or background-check claims. Student accounts cannot apply as adult organizers.

The four-stage listing editor covers title, event/activity type, interest category, uploaded image with local preview, day/date, start/end time, IANA time zone, venue, street address, area, description, age range, languages, capacity, price, request deadline, supervision, accessibility, cancellation terms, and optional business contact details. Private uploads can be edited without public storage URLs or a forced reupload. Drafts require a title, category, and starting date but may leave venue and description unfinished. Submission requires complete required details and a future start date. Saving a draft or submitting edits never publishes automatically; staff review is retained.

Business contact name, phone, and HTTP/HTTPS website appear on the public detail page only with explicit organizer contact sharing enabled. There is no Gmail integration or email requirement. Venue addresses link to OpenStreetMap search; no child location or live GPS is collected.

Each listing's private manager provides a preview, individual activity sessions, status/session filters, pending decisions, and confirmed attendees. Only the owning verified organizer or that school's verified staff can access it. Pre-parent-approval interest is an aggregate count; child nicknames and age bands appear only after parental approval. Parent-declined interests are not shared. Parent contact details and attendee lists are never public. Owning organizers can approve/decline eligible requests through the same capacity-locked services used by staff, with decision actor/time recorded.

Organizers may add or edit their activity sessions, but those changes send the activity back for staff review. Every session remains a distinct allocation. Cancellation requires a reason and confirmation, closes all sessions and active ticket/family requests transactionally, preserves request history, and creates in-app notices. Cancelled listings disappear from discovery but their approved public detail pages retain a cancellation notice. They cannot be reopened by ordinary edits; create a new listing for another date.

The additive `0005_event_address_event_cancellation_note_and_more` migration preserves existing listings. No new environment variables, paid services, Gmail, or outbound email are introduced. `community.test_organizers` covers ownership, public/private contact data, drafts, access applications, parent consent boundaries, cancellation, and private-image editing. The organizer browser workflow covers application → staff access approval → draft → image upload → submission → staff publication → attendee confirmation → cancellation at mobile, tablet, and desktop sizes.

## Tech Week: no-registration presentation

Anonymous visitors to `/` now see the interactive presentation. `/demo/` is its permanent entry link, including for visitors who are already signed in. Parent and organizer demonstrations require **no email, password, signup, or access approval**.

- Parent view: `/demo/family/` — fictional profiles, sample requests, simulated parent approval, and status tracking.
- Organizer view: `/demo/organizer/` — post/edit a sample event, preview a local image, choose date/time/place/interests/contact details, and simulate attendee confirmation or cancellation.
- Events, Activities, Saved, and Activity Finder are also available under `/demo/`. The demo finder uses fictional in-memory filters, not a live AI service. Only `/finder/` calls Claude.
- Presentation changes now use sessionStorage in the current tab. Requests, approvals, bookmarks and presenter progress survive reloads; Reset Demo clears the checkpoint. No demo data is written to the live database or localStorage. Closing the tab ends its browser session. See [Final presentation release](docs/TECH_WEEK_FINAL.md) for the updated flow and checks.
- **Reset demo** restores the fictional examples for the next visitor. It does not clear real account sessions, application records, or accessibility preferences.

All sample content is marked Demo and does not advertise real events, venues, capacity, organizer verification, or confirmed bookings. Visitors are instructed to use invented names. No real accounts are provisioned, no emails are sent, and no server-side event or family records are created by the demonstration. Real account authorization, staff verification, and parent password checks remain intact on the live routes.

`/community/` continues to expose the real public community listings; signed-in users retain their normal homepage at `/`. The presentation links are visible in the live UI too. No new environment variables or migrations are needed. Share `/demo/` at Tech Week for a consistent registration-free entry point on any device.

`community.test_demo` and the presentation browser workflow test public access, separation from real private data, role switching, browser-only posting, approval simulation, reset, and isolation between visitors. The final demo browser suite is `community.browser_demo_final`.

### AI explanations in demo activity details

The existing server-only `ANTHROPIC_API_KEY` also enables short Claude match explanations in `/demo/events/.../`. Only fictional age, enumerated interests/languages, and activity age/category/languages are sent. A successful response displays “✦ AI match” with a deterministic estimated profile-fit percentage (age 40%, interests 40%, language 20%). Missing credits, missing keys, timeouts and invalid responses fall back to a clearly labelled profile match. No real child records are read or sent; no bookings or approvals are changed. Scores are not safety checks or calibrated probabilities.

### Voice search

Discover now includes microphone input with parent agreement, browser permission, an editable transcript and an explicit **Search with AI** action. Both demo and live searches use the existing Claude interpreter; several spoken interests can match several categories. Unsupported browsers retain typed search. See [voice search implementation and privacy notes](docs/VOICE_SEARCH.md).

### Organiser AI drafts

**Fill with AI ✦** turns a one-sentence brief into proposed title, description, ages, category, languages and accessibility fields in demo and live organiser editors. Review the proposal, apply it, edit freely, then save or submit through the existing workflow. No dates, prices or publishing actions are generated. Unknown facts leave existing values unchanged. See [organiser AI implementation](docs/ORGANIZER_AI.md).

### Advisory demo moderation

New demo submissions are screened for risky wording, missing information and age fit. Valid AI results show **Safe** (no concerns detected in the text) or **Needs review**, with reasons; local concerns cannot be overridden by AI. Missing credits or failed checks always require manual review. Admins retain the final approval/rejection decision. Reports persist through refresh and are invalidated by edits. See [Demo moderation](docs/DEMO_MODERATION.md).

### AI visual effects

Shared hero glow, glass cards, brief AI-star shimmer, answer typing and hover lift support reduced motion. See [visual effects and accessibility](docs/AI_VISUAL_EFFECTS.md).

### Ask TK assistant

A floating **✦ Ask TK** opens an accessible activity assistant throughout the shared app pages. Claude interprets preferences, while the catalogue controls the suggestions. **Browse catalogue without AI** works without credits. Chat is held only in the current page, cleared on close/reload, and never written to application storage. See [Ask TK privacy and verification](docs/ASK_TK.md).

### Activity imagery and link previews

Activity cards and details use activity-led, locally hosted illustrations matched to subject, approximate ages and indoor/outdoor setting. Generic Lisbon cityscapes are never used as event covers. Uploaded images need descriptive alt text, an honest source label and organiser review against current event details. Uncertain matches use a placeholder. Shared pages include an absolute, public 1200 × 630 Open Graph/Twitter preview. See [activity-image policy](docs/ACTIVITY_IMAGE_POLICY.md) and [sharing checks](docs/CITY_IMAGERY.md).

### Brand and role consistency

The interface uses the home-screen violet/orange tokens, colourful About Us panels and restrained decorative backgrounds. Sophia Gatenyo's corrected name includes a safe portrait/profile data migration. Signed-in demo roles follow accounts; studio pages and APIs reject child, parent and unverified-organiser access. Guest presentation roles remain explicit fictional simulations. See [brand and role changes](docs/BRAND_ROLE_REFRESH.md).
