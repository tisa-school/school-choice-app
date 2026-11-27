## Change
TK-ZONE is a Django/server-rendered application, so this keeps its Vercel/Neon backend and bundles a local Capacitor frontend. It brings the existing mobile projects into the current branch and extends the native/local discovery experience with school search, two-or-three-school comparison and a seven-day offline public library.

Offline downloads use dedicated public-only API endpoints and an allowlisted IndexedDB projection. Private membership events, family profiles, requests, messages and auth tokens are excluded. Downloads have expiry/removal controls, stale-data warnings and are cleared on logout/deletion request. Existing saved account data remains in the backend. Existing website routes and production deployment are preserved; mobile APIs remain opt-in.

Includes iOS/Android icons, splash/configuration, secure session/calendar adapters, bounded offline requests, Android back fallback, aligned version labels, tests and unsigned native compilation CI jobs. Advanced hosted workspaces remain browser links requiring their own website session.

## Verification
- 319 Django tests passed, including 20 mobile API tests.
- Nine mobile unit/security/cache tests passed.
- TypeScript and Vite release build, Capacitor iOS/Android sync passed.
- Chromium tests cover login, five activity filters, saved items, parent approval, school search/comparison, disconnected reading, expiry/removal and 390/768/1440 width checks; existing discovery/navigation browser suites were also exercised. Final five-test Chromium run passed. Details in docs/MOBILE_STORE_READINESS.md.
- Isolated Vercel preview-build check uses synthetic configuration only, never a production database.
- Screenshots: artifacts/mobile/comparison.png and offline.png.

## Release gates — draft, do not merge/deploy yet
Android bundleRelease was attempted but blocked fetching Gradle (services.gradle.org DNS/network access); no AAB exists. Xcode is unavailable on Linux; no archive, signed install or native device test was run. Added GitHub native compilation jobs are unverified until CI executes. Live Vercel access was blocked by proxy policy; actual remote mobile APIs are not verified.

Publisher must complete signing/device testing, native WebView HTTP/login/safe-area/offline cold launch, backend preview/production approval, operational account/data deletion, community user blocking/moderation operations, child/guardian consent and truthful privacy/AI disclosures. No store upload, payment, production migration or live deployment was performed. Exact TestFlight/Play submission commands and remaining steps are in docs/MOBILE_STORE_READINESS.md and docs/MOBILE_APP.md.
