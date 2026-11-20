# Restore the selected final website — 20 November 2026

The user selected `83a5d9b8efc5a76ff3be2b8a5c399735cded0788`, whose parent is `7019fc3633f941c5d316ee7643d8be2224236b55`, as the final public website. This restoration supersedes the later five-section redesign.

## Restored

- The original “Big discoveries for little explorers.” homepage, activity illustration, interests and discovery sections.
- The complete unified sidebar, original header/footer, category and school pages, saved pages and original three-school comparison.
- The original presentation navigation and working legacy links.

The original homepage template, navigation definition and presentation navigation script are taken directly from the requested commit. A small, separate `photo-admin.css` adds only photo-related styles. The later editorial design stylesheet does not load on the restored public pages.

## Administrator photo feature retained

Verified Unicorn School staff and super administrators can open About Us, select Daniel's existing `student-3` card, choose Add/Change photo, preview, save, replace or delete the photo. JPG, PNG and WebP validation, private database-backed storage on Vercel, server-side school permissions, CSRF checks, existing-account sign-in and reload/new-login persistence remain in place.

About Us shows clear sign-in/permission guidance instead of silently hiding controls. The dedicated `/manage/team/` photo editor remains available for cropping. Selecting an administrator demo role does not grant real upload permissions. Public sharing of child portraits continues to require the existing consent/review workflow.

## Data and release safety

This is a new forward commit, not a Git history reset. All existing database models and migrations remain present. No migration is reversed, no database is replaced and no production record is deleted by this restoration. Saved experiences and private family photo records introduced by the later release remain stored and accessible. Management styles are scoped to management pages.

The separate school-directory/QR branch is not substituted for the explicitly selected commit. No new dependency, service key or database branch is needed for this restoration.

The earlier PLATFORM_V2 release report and screenshots describe a superseded public layout; they are retained as history, not the design being deployed now.

## Verification

Results are recorded after running backend and real-browser regressions, including the restored homepage/sidebar and administrator upload, replacement, refresh, new login and deletion. Hosted deployment status must be checked separately; a successful GitHub push alone is not proof that Vercel is Ready.

### Results

- **336 tests passed** in one final combined run (242.447 seconds): 296 backend tests and 40 Chromium browser workflows.
- All five JavaScript test scripts passed; modified scripts passed syntax checks.
- Django checks and migration-drift validation passed. There are no model or migration changes in this release.
- The Vercel preview build script passed with isolated dummy configuration. This checks code/static collection; hosted PostgreSQL and deployment health are not established by that local build.
- Local mobile/desktop performance budgets passed; see `RESTORATION_PERFORMANCE.json`. These are synthetic local measurements, not production Core Web Vitals.
- The fictional weekly-summary browser test pins its November demo calendar date; no real event date or catalogue entry was changed.

Screenshots below show the implemented restored interface. The About Us photo-control screenshot uses an isolated administrator and a solid-colour test image, not Daniel's real photograph or production data.

- [Restored desktop homepage](screenshots/restored-83a5d9b-home-desktop.png)
- [Restored mobile homepage](screenshots/restored-83a5d9b-home-mobile.png)
- [About Us administrator photo controls](screenshots/restored-about-photo-controls.png)

## Visible photo-button follow-up

Each contributor card now has a visible Add photo / Change photo entry in both `/about/` and `/demo/about/`. Visitors follow the button through real administrator sign-in to the existing protected editor; the button itself grants no role or upload permission. Authorised inline upload forms have an actual Add photo button that opens the file picker, followed by preview and Save photo. The button changes to Change photo after saving.

Accessible descriptions reference existing team headings so contributor names and leadership credits are not duplicated. The selected homepage and sidebar remain unchanged. No real portrait was inserted by this code change: the earlier inline chat image was unavailable as a workspace file, and no live database/admin session was connected.

Verification: 35 focused backend tests and seven real-browser workflows passed, including the visible button in both About Us views, real sign-in, native file selection, saved-photo persistence, and unauthorised denial. JavaScript syntax, migration drift and the isolated preview build were also checked.
