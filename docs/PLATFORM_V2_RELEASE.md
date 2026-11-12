# TK-ZONE 2.0 implementation and release notes

This upgrade extends the existing Django application. It does not replace its database, original IDs, ticketing, saved collections, organiser workflow or demo session journal. The new route namespace is `/manage/` for management and `/tour/` for the consolidated product tour. Legacy links remain available for compatibility; prototype tools are absent from primary navigation.

## Phase evidence and limitations

| Phase | Implemented | Verification and remaining work |
| --- | --- | --- |
| 1: Stabilisation | Existing-account email **or username** sign-in; ambiguous identities rejected; original authentication backend retained for old sessions. Verified school staff can use `/manage/` without granting Django superuser/staff flags. Dedicated editor opens Daniel Vinnikov's existing `student-3` roster entry. Private, validated JPG/PNG/WebP uploads support preview, crop, replacement and deletion. | Isolated database and browser tests verify Daniel's stable photo record, crop, replacement, refresh, new login and unauthorised denial. No production account or Daniel photograph was supplied. Live identity/role and media cannot be certified. |
| 2: Navigation and home | Five shared destinations: Discover, Activities, Schools, My Family, Community. Role-specific account menu, global search, editorial homepage, eight working interest groups, private week preview and policy footer. | Desktop/mobile link, active destination, keyboard drawer and EN/PT checks. An editorial composition is used instead of unauthorised photography. |
| 3: Schools | Existing directory retained; four-school comparison, favourites, transport facts, consent-aware gallery, official source/date publication checks and empty location default. Protected research queue creates unpublished drafts idempotently. | Comparison/save tests pass in isolation. New official school facts and photo permissions remain **unverified**: outbound access to the requested school domains was denied with CONNECT 403. User-supplied research targets are not published facts. Distance is marked unavailable until valid origin and verified coordinates are available. |
| 4: Activities | Existing scheduled events and recurring sessions retained; public/scoped search, eight interest groups, combined filters and sorting. Added sourced ongoing/by-appointment/proposed/unverified experience model, private planning, save/share/map/official links. Event source dates are visible where recorded. | Local search, privacy, save and calendar tests. Unscheduled experiences do not appear under date-specific filters or claim booking availability. No new real Benfica/MAAT/Unicorn Factory programme was fabricated or published. Research and licensed photos still require official-source access. Search uses database filtering/indexes; no integrated geocoded results map is claimed. |
| 5: My Family | Private child interests, preferred activity types and cropped photos; unified saved activities/schools/experiences; week/month calendar; private event create/edit/remove; duplicate constraints; ICS export; persistence across sign-ins. | Owner and cross-family privacy tests plus real-browser signup/photo/save/plan/export/logout/login. Calendar entries are explicitly plans, not bookings. |
| 6: Product tour | One eight-step tour in Help, with progress/back/next/skip/restart, read-only public catalogue and isolated session sandbox. Protected administrator tour adds simulated moderation. | Eight-step browser walkthrough and no-POST/no-business-record-write tests, including no accidental scheduled-announcement publishing or preference writes. Empty catalogues use explicitly fictional fallback samples. Legacy bookmarked demos are retained for existing links, not promoted as new production features. |
| 7: Management | Scoped real-data dashboard; users, families, children, schools, activities, experiences, organisers, reports, portraits, school media, audit, diagnostics and super-admin settings. Publish/unpublish/archive/delete protections, CSRF and account-change password confirmation. | Role/school scope, audit, CRUD, publication, review and protected-media tests. User role elevation still requires the trusted existing operator process; there is no public administrator registration. Deletion of events with participation, ticket, booking or family-plan history is refused. |
| 8: QA | Automated backend/browser/JavaScript checks, migration validation, preview build script and local performance artifact. | See final verification below. Live Vercel runtime/database, production credentials, real email delivery and external source verification remain unverified. No WCAG certification or production Core Web Vitals claim. |

## Important design and scope decisions

- The new five-section request supersedes the previous long sidebar order and the earlier three-school limit. Existing saved relationships are reused, not migrated into a new disconnected store.
- Django is retained; older Next.js instructions do not apply to this repository.
- Real family/administrator actions persist to the database. Tour actions never do. The existing demonstration journal keeps its separate storage keys.
- English and European Portuguese use the existing shared catalogue. Existing additional language choices remain available, with English fallback for new untranslated copy. Authored event descriptions are not automatically translated by AI.
- Existing supplied/generated event covers remain subject to the image-review policy. Unapproved images are not promoted to factual event photography. No school photo is copied without permission.
- The local database was empty of real users and portraits at audit. A real production administrator repair cannot be confirmed by creating an unrelated local account.
- Source research and production identity verification are blocked dependencies. Independent implementation proceeded without publishing unverified records or modifying the live database.

## Trusted operator: existing administrator and Daniel

1. Deploy/migrate a reviewed version against the intended database, then sign in through `/accounts/login/` with the **existing** username or email and password.
2. Use `/manage/diagnostics/` to inspect non-secret readiness metadata. `/health/` reports only schema/database readiness, not full application health.
3. If an existing school administrator lacks verified membership, a trusted operator can run `python manage.py grant_staff --email EXISTING_ADDRESS --school-id EXISTING_SCHOOL_ID` after verifying ownership. It refuses missing, ambiguous or inactive accounts and cross-school reassignment. It does not create a password or superuser.
4. In `/manage/team/`, open **Daniel Vinnikov**. Use the existing `student-3` identity. If Unicorn School is missing or ambiguous, a super administrator must select the real project school in Site Settings. Do not create another Daniel profile or guess the school.
5. Upload an authorised photograph, adjust crop, save, refresh, sign out and back in. Confirm replacement/deletion and unauthorised denial against the real deployment. Photos remain private unless the established separate publication/consent workflow is completed.

## Safe deployment and migrations

Seven additive migrations (`0015`–`0021`) introduce management audit/settings, private family media/events, source-backed experiences and school media, category/index/archive fields, and explicit school locations. They do not seed live events, staff credentials, school research facts or photographs.

1. Back up the intended database and private media. Use a separate preview database with no real child data.
2. Set preview-only `DATABASE_URL`, persistent `DJANGO_SECRET_KEY`, appropriate `DJANGO_EMAIL_BACKEND` and host/CSRF configuration through Vercel environment settings. Never paste secrets into commits, PRs or chat. Console email is **not** functioning account recovery; configure and test an actual delivery provider before relying on recovery.
3. Apply `python manage.py migrate --noinput` to the isolated preview database using a trusted environment. The Vercel **preview** build deliberately does not run migrations against a potentially shared production database.
4. Deploy the feature branch preview. `/health/` must return 200, then perform the visitor, family, administrator and tour walkthroughs below. A successful build is not runtime verification.
5. Only after review and explicit release approval should main be merged. The existing production build then runs its existing migration step. Do not connect an unreviewed preview to production records.
6. For rollback, revert the application release while retaining additive schema and restore a tested backup if necessary. Migration reversal is available through Django but drops newly stored data; do not reverse migrations on live records without backup and explicit data review.

## Local verification commands

```sh
python manage.py collectstatic --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test community --noinput
node --test static/community/*.test.cjs
```

Browser modules use an isolated test database, Chromium and Playwright; they do not seed application data. Run them sequentially with other Django test commands because local SQLite uses a shared test database filename. CI backend checks also run against PostgreSQL 16; that remote result is not established by local SQLite tests.

The Vercel build script was exercised with `VERCEL_ENV=preview` and dummy non-production configuration. This proves checks/static collection, not remote database connectivity or a hosted deployment.

`PLATFORM_V2_LOCAL_PERFORMANCE.json` records local synthetic mobile/desktop FCP/LCP, CLS, document and script budgets. It uses an empty catalogue without real photos. INP and production field performance are not measured.

## Review walkthrough

1. Open Discover at 390px and desktop widths; search football, combine age/area/date/budget, follow activity details and official links.
2. Open Schools; select four, compare facts and keep a shortlist. Unknown data must remain explicitly unavailable.
3. Create an isolated parent account, add a private child profile/photo, save an activity, add a plan and private event. Export ICS; sign out and back in to confirm persistence.
4. With a verified existing administrator, open Management; edit Daniel's portrait, create a sourced school and activity draft, publish/unpublish/archive, inspect the audit record. Verify child/parent accounts cannot open the same routes.
5. Help → Interactive Product Tour. Complete all eight steps, restart, then confirm production saves, profile records and calendar were unchanged.

Screenshots in `docs/screenshots/platform-v2-*` show the implemented interface with isolated, clearly named test fixtures. They are not evidence of published real school/event data or a production administrator account.

## Implemented-interface screenshots

All are captured from the application, using an isolated test database. The named test schools/event and solid-colour photo fixture are not published real records.

- [Discover desktop](screenshots/platform-v2-discover.png)
- [Discover mobile in European Portuguese](screenshots/platform-v2-discover-mobile.png)
- [Four-school comparison](screenshots/platform-v2-school-comparison.png)
- [Daniel's existing roster editor](screenshots/platform-v2-daniel-editor.png)

## Final verification

- Chromium/Playwright: **39 browser tests passed** (157.503 seconds). Includes new and existing workflows, combined filters, private uploads, tour isolation, role restrictions and responsive layouts.
- JavaScript: all **5 test scripts passed** under Node's test runner. New and modified browser scripts passed syntax checks.
- Django configuration check and migration drift check: passed.
- Vercel preview build script with isolated dummy configuration: passed; it runs checks/static collection and deliberately skips database migrations for previews.
- Local performance budgets: passed at 390px/1440px. FCP/LCP 220ms/224ms, CLS 0; see the JSON artifact for scope and limits. These are not production measurements.
- Django: **294 backend tests passed** (56.314 seconds), including privacy, authorisation, validation, persistence, migrations and the existing workflows.
- Development branch: `feature/tk-zone-2`. Main is preserved. GitHub CLI authentication is unavailable, so automatic PR creation and remote CI status are unverified. Vercel credentials/access are unavailable; a hosted preview cannot be certified from this environment.

## About Us administrator photo follow-up

About Us now highlights the authorised photo-management area above the team. Each existing team card provides Add photo / Change photo, a local image preview, Save photo and Delete photo. Controls and private media remain permission-checked by the existing server endpoints; no separate team identities or public administrator shortcuts were added. The dedicated management page still provides cropping.

Verified with 26 focused backend tests and two Chromium workflows, including direct About Us upload, replacement, reload, deletion and signed-out denial. This code is on the feature branch; it does not establish that the production deployment or a particular live account has received it.

### Missing photo buttons

About Us provides an Administrator photo access sign-in entry for visitors. Signed-in users without a verified administrator role see a permission explanation. Authorised administrators whose Unicorn School context cannot be resolved see a configuration message; super administrators can open Site Settings to select the existing school. The system does not grant upload access from a demo role selector. These states have focused regression coverage.

GitHub main remained at `83a5d9b` during this investigation; the feature-branch fixes were not merged into production. The absence of a button alone does not establish a storage/upload error or the live account's role.
