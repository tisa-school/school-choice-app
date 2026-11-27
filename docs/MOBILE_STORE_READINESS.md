# TK-ZONE mobile implementation and publisher handoff

Date: 27 November 2026. This work is on the current `feature/subscription-demo` branch; its historical name does not imply a payment integration. The existing `b2be893` Capacitor implementation was brought into this branch, then extended. No subscription, real charge, live deployment, production migration or store submission is part of this change.

## Architecture audit

The repo is Django 5.2, Python, server-rendered templates in `templates/`, and progressive JavaScript in `static/community/`. It is not Next.js or a static SPA export. `config/urls.py` owns routing; `community/discovery.py` is the shared listing visibility policy. Production runs on Vercel with PostgreSQL/Neon configured by `DATABASE_URL`.

The website authenticates with Django cookies/CSRF; `community/authentication.py` supports existing username/email identities and hashed passwords. `SavedEvent` stores user/event relationships, `ShortlistedSchool` stores user/public-school relationships, and collections and experiences have their own existing tables. These records persist in the backend; mobile does not replace them. Existing saved collections/advanced workspaces stay accessible through the hosted website.

Capacitor 8 bundles a local Vite/TypeScript frontend, fonts, branded icons and splash assets. No iframe and no remote `server.url` are configured. The app uses opt-in `/mobile/v1/` JSON APIs with expiring bearer sessions, whose hashes are stored in Neon. Raw tokens are held in iOS Keychain / Android Keystore-backed storage. Website cookies cannot bypass mobile authentication. The API reuses existing filters, school visibility, parent decisions, saves and capacity services. It remains disabled by default until a separately approved backend deployment.

Mobile routes use local hash navigation. Android Back falls back to Home when no earlier route exists; on Home it minimises the app. iOS safe-area insets apply to the header and bottom tabs. These adapters are implemented but real Android/iPhone execution still needs device verification. Native HTTP uses CapacitorHttp with the configured HTTPS origin. Browser validation uses credential-free fetch and the same backend APIs. Authentication URLs never carry tokens.

Native/local screens now cover activity search and combined filters, details, school name/area/language/curriculum search, two-or-three-school comparison, school details, saved schools/activities, login/parent signup, parent requests/decisions, plans/calendar and notifications. Existing community, About Us/photo administration, AI Finder and organiser management open in a native browser and may require a separate website login. They are preserved, not all rebuilt as native screens.

## Offline public library

A person explicitly chooses **Download public details** on a public activity or school. `/mobile/v1/public/events/<id>/` only returns public, published, non-archived listings with a publisher. School detail/comparison endpoints only return published, non-archived directory profiles. Private membership-only events cannot be downloaded, even by a signed-in member.

`mobile/src/offline.mjs` projects each response onto an allowlist before writing IndexedDB. It excludes tokens, names of account holders/children, family profiles/photos, requests, decisions, messages, saved-account flags and session metadata. Restoring a copy applies the projection again. The library holds at most 50 text-only public snapshots, each expiring exactly seven days after download. There is no background cache of arbitrary API responses and no offline mutation queue. A selected list of public downloads can itself reveal interests on a shared device; downloading is explicit and deletion controls are prominent.

The Offline library is available without authentication from More and connection-error pages. Copies show download/expiry times and a warning to recheck dates, availability and fees online. Removing one copy, clearing all, logout and an account-deletion request remove local copies. Expired copies are purged when the library is read. Server changes/unpublishing cannot remotely retract a disconnected device's copy before expiry; disclose this limit. No private content is used to make offline matching decisions.

The bundled native shell can open without downloading website HTML; IndexedDB still needs testing on physical iPhones/Android devices, including app restart, OS storage eviction and upgrade. The browser test verifies rendering and reads while network requests are disabled, not a native cold launch. This is useful functionality for a store reviewer, not a guarantee of Apple's minimum-functionality acceptance.

## Community/family audit and store blockers

Evidence comes from repository code; a live-site request was blocked by environment proxy policy (403), so deployed behaviour and configuration were not verified.

| Area | Existing behaviour | Publisher/release gap |
|---|---|---|
| Community content | `community/community_views.py`: parents/guardians or authorised adults can submit experiences/photos; submissions and edits enter `pending`. School-scoped verified staff/superusers review publish/hide decisions. Published contributions can be reported; authors can delete theirs. | No user-facing block/mute-author mechanism was found. Implement and test suitable user blocking before exposing UGC in a store release, or remove that surface from the mobile release. Confirm community rules, abuse contact, review staffing and response process. Reports are not automatic safeguarding checks. |
| Children/family | `ParentAccount`, private `ChildProfile` (nickname, age band, interests, languages, optional photo), participation histories, private calendar notes; server checks parent ownership, password confirmation and organiser admission separately. | A checkbox is not verified guardian identity. Review consent, age assurance, legal basis, child-photo permissions and the chosen store audience. Do not claim safeguarding verification. |
| Account deletion | Password-confirmed mobile request creates `MobileDeletionRequest`, revokes mobile sessions and deletes push registrations. Superusers can inspect the queue. | It does not finish deletion. A working account/data deletion and retention process, including protected organiser records, backups and stored photos, must be implemented/tested before submission. Google also needs an accessible external deletion-request URL. The current privacy page is not proof of such a process. |
| Private uploads | `community/storage.py` and upload forms validate raster files/size, store private media in PostgreSQL on Vercel, and permission-check media routes. | Database records and `PrivateUpload` blob lifecycle must be included in deletion/retention verification; cascading a profile alone does not prove all orphan blobs/backups are purged. |
| Authentication/recovery | Existing hashed-password accounts, email/username login, CSRF and school-scoped authorisation. Mobile sessions expire/revoke. | Publisher must configure and test recovery email, secret management, real-device token restore/logout/expiry, and denied access. Never publish a key copied from chat. |
| AI | `community/finder.py` forwards up to 500 characters of user-entered preferences to Anthropic when configured. Demo explanation/moderation/draft/summary modules also have optional provider calls. | Instructions asking the model to omit names do not remove personal information before transmission. Review explicit disclosure/permission for third-party AI, minimisation and age suitability before including linked AI surfaces. Do not claim all text stays on device. |
| Notifications | Private in-app inbox; optional adult opt-in APNs/FCM registration and generic lock-screen messages. | Signing/APNs/FCM credentials, delivery, revocation and an idempotent background-delivery workflow are not validated. No push was sent in these tests. |
| Store audience | No private child-to-child chat, ads, precise GPS or contacts permission was added. | Publisher must choose truthful age ratings, Kids/Families eligibility, parental gates for relevant external links, and required school/guardian authorisations. Do not label the app Kids Category-ready without that review. |

## Privacy disclosure worksheet (code-based, not completed store declarations)

| Information | Where used/stored | Potential recipient |
|---|---|---|
| Account email/username/display name and password hash | Django User, backend PostgreSQL; credentials sent over HTTPS for authentication | App operator; Vercel/Neon infrastructure; configured recovery-email provider for email |
| Child nickname, age band, interests, languages, optional photo | Access-controlled family profiles/media in backend | Parent and authorised staff/functions according to existing routes; hosting/database processors |
| Saved schools/activities, collections, plans, participation and history | Backend records linked to account | Operator/backend processors; relevant authorised organiser/staff for requests |
| Community text/photos, author attribution, reports and moderation actions | Moderated backend content; published content can be seen by permitted audiences | Audience of the published listing; moderators and processors |
| Device push tokens and session metadata | MobileSession/MobilePushDevice server tables; session secret in native secure storage | Operator; APNs/FCM when delivery is configured |
| Search/AI text | Normal filters go to Django; optional AI preference prompts go to Anthropic | Operator, configured AI provider; provider retention settings must be verified |
| Public offline listing snapshots and language preference | Device IndexedDB/local preference only | No additional upload by this feature; someone using the same device can view downloads |
| Network/security metadata | Existing rate limiting uses hashed actor/IP/path keys; infrastructure may log network requests | Operator and hosting providers; inspect actual logging/retention configuration |

No analytics/advertising SDK, precise location tracking, contact-book access or payment handling was added by this change. Calendar editor integration exports a plan only after the user's action; Android does not request calendar read/write access, iOS17+ requests write-only event access and iOS15/16 uses legacy EventKit permission. System speech/browser providers in hosted features need their own disclosure review. The app bundles third-party Capacitor privacy manifests; the publisher must inspect the final archive manifests, required-reason APIs and dependencies rather than assuming an empty data-collection label.

## Build and signing steps

An authorised adult publisher should manage developer-account agreements, organisation details, signing and submission. Keep signing files, passwords, APNs keys and Firebase service accounts out of Git. Confirm the provisional application ID `org.unicornschool.tkzone` before store registration.

1. Configure an isolated HTTPS preview backend with the branch's Django code, separate Neon database, secret/recovery-email setup, migrations and `MOBILE_API_ENABLED=1`. Test `/health/` and `/mobile/v1/capabilities/`. The existing production site is unchanged; it will not magically have the new API. Production migration/merge needs separate approval.
2. Set only the public origin in `mobile/.env.local`:

   ```dotenv
   VITE_API_BASE_URL=https://YOUR-APPROVED-BACKEND.vercel.app
   ```

3. Install Node24 and build/sync:

   ```bash
   cd mobile
   npm ci
   npm run build
   npm test
   npx cap sync
   ```

4. Android: Android Studio, SDK36, JDK21, API24+ emulator/device. Open and run; test Back, permission denial, login persistence, search, comparison and airplane mode:

   ```bash
   npx cap open android
   cd android
   ./gradlew testDebugUnitTest
   ./gradlew connectedDebugAndroidTest
   ./gradlew bundleRelease
   ```

   Expected bundle location: `app/build/outputs/bundle/release/app-release.aab`. Without a configured release signing identity this is not a Play-upload-ready signed artefact. In Android Studio choose **Build → Generate Signed Bundle / APK → Android App Bundle**, use an external protected upload keystore, and choose release. Store upload/recovery credentials separately. Increment versionCode for each subsequent upload. No debug key fallback is added.

5. iOS requires a Mac and Xcode compatible with Capacitor8. Open `mobile/ios/App/App.xcodeproj`, choose App, configure a development team/signing profile and confirmed bundle ID, resolve Swift packages, then run on simulator/device:

   ```bash
   npx cap open ios
   xcodebuild -project ios/App/App.xcodeproj -scheme App \
     -configuration Debug -sdk iphonesimulator \
     -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
   xcodebuild -project ios/App/App.xcodeproj -scheme App \
     -configuration Release -destination 'generic/platform=iOS' \
     -archivePath "$PWD/release/TK-ZONE.xcarchive" archive
   ```

   These commands are relative to `mobile/`; return there after Android commands. The archive requires your valid signing configuration. In Xcode Organizer choose **Distribute App → App Store Connect** only when the publisher is ready. No IPA/archive exists merely because `cap sync` succeeds. Native secure storage, WKWebView routing/HTTP, safe areas, calendar and offline cold launch remain device gates.

## TestFlight and Google Play handoff

An authorised adult publisher should handle developer agreements, identity verification, signing credentials and store submission. Students can continue developing and testing without putting those credentials in Git.

- Complete the blockers above, deploy/verify the approved backend, select final IDs, increment version/build numbers and prepare real screenshots from signed device builds.
- Apple: create App Store Connect record; add app name, bundle ID, category/age rating, support/privacy URLs, reviewed App Privacy disclosures and export-compliance answers. Upload a signed archive through Organizer; wait for processing; add internal TestFlight testers first. External TestFlight and App Store review may require review. Supply a functioning review account and clear steps to demonstrate offline saved public listings. Explain family permissions and moderated content truthfully.
- Google: create Play Console record; finish developer/organisation verification, listing, content rating, target audience/Families review, Data Safety, privacy/support and external deletion URL. Configure Play App Signing; upload a properly signed AAB to internal testing. Fulfil the testing/access requirements shown for the publisher's account before requesting production access. Do not assume a fixed testing duration applies to every account.
- Exercise signed installs on real devices: fresh signup/login, recovery, wrong password, session expiry/revoke, school comparison, saved lists after restart, offline cold launch, seven-day expiry, logout clearing downloads, OS storage eviction, airplane mode during writes, Android back/root behaviour, iPhone notch/home-indicator/keyboard, text size, VoiceOver/TalkBack, calendar/push permission denial and account-deletion fulfilment.
- Submission is left to the publisher. No merge, store upload or live backend change is authorised by this handoff.

## Verification results

See the final results below once commands complete. Existing setup commands and integration limitations are also in `docs/MOBILE_APP.md`. Screenshots in `artifacts/mobile/` use isolated fictional fixtures, not real family data.

Executed locally for this update:

| Check | Result |
|---|---|
| Django system check; migration drift | Pass; no new model migration needed for this update |
| `python manage.py test community --noinput` | 319 passed, including 20 mobile API tests |
| Final combined Chromium suites | Five tests passed: the extended mobile journey plus four existing discovery/navigation tests |
| Extended mobile Chromium journey | Passed: login, five combined activity filters, save, parent permission, calendar, school search/comparison, downloaded public details, disconnected reads, expiry/removal, reconnection and school save; widths 390/768/1440 checked for horizontal overflow |
| `npm run build` | TypeScript checking and Vite release bundle passed |
| `npm test` | Nine mobile unit/security/cache checks passed |
| `npx cap sync` | Android and iOS assets/plugins synchronised |
| `sh scripts/vercel-build.sh` with isolated synthetic Preview configuration | Passed; no production database connection/migration |
| `./gradlew bundleRelease` | Attempted; failed fetching Gradle distribution (`UnknownHostException: services.gradle.org`). No AAB produced. Android SDK tools/device were not available here |
| iOS archive/device tests | Not run: Linux environment has no Xcode or Apple signing environment. No archive/IPA produced |
| Live Vercel check | Blocked by environment proxy (403); no claim that deployed APIs work |
| Signed installs, actual WebView HTTP/login/storage, Android hardware Back, iPhone safe areas, APNs/FCM | Not verified on devices; publisher testing gates remain |

GitHub Actions now includes unsigned Android bundle/unit-test and unsigned iOS simulator compilation jobs. Those workflows were added, not executed locally; their eventual CI results must be checked. An unsigned CI artefact is not store-signable without the publisher's signing workflow. No workflow uploads anything to a store or deploys the live website.
