# Production release audit — 6 November 2026

The supported website is https://school-choice-app-hrvb.vercel.app/.

## Findings and completed changes

- The anonymous homepage previously opened a separate browser-only presentation. The homepage now uses the real event and activity database. Navigation opens authenticated family, saved-item and organizer workflows. Previously shared URLs remain compatible and lead to real pages; selecting an old role parameter cannot grant permissions. No sample accounts, events or bookings are imported into production.
- The Activity Finder now offers validated category, age, language, area, date, price and keyword filters without an AI service. Optional preference interpretation remains available only when its provider is configured and the user consents. Results always come from visible database listings.
- About Us staff controls now support publishing a saved portrait and making it private. Public sharing requires an explicit permission declaration including guardian consent for children. Upload replacements still start private; staff can publish them themselves. Existing public portraits are preserved. Generic form-saving indicators no longer remain stuck after asynchronous photo actions.
- General feedback is assigned to the official school when that school is unambiguous. Previously unassigned feedback is reviewable only by verified staff of the unique official school. Other schools and parents cannot access it.
- Verified school staff can configure a private school invitation code in School access after entering their password. Only the hash is stored. Existing accounts do not gain staff privileges by joining.
- New controls are translated in all supported interface languages. Older browser tests were updated for current full names, capacity labels and language application controls.
- Real-browser regression checks are now part of GitHub Actions alongside PostgreSQL checks.

## Verification

The release is checked with Django tests, PostgreSQL CI, Node tests, JavaScript syntax checks, migration-drift checks, static collection and the Vercel build script. Browser checks use isolated records and synthetic images, never live registrations.

Browser journeys cover:

1. Staff event creation; student signup and school joining; search, saved items and collections; ticket approval and wallet; announcements; notifications; profile preferences.
2. Public discovery and private-listing isolation; activity/session creation; parent setup and child profiles; parent approval, organizer confirmation and family planning.
3. Organizer application, staff review, draft editing, image uploads, submission review, attendee management and cancellation with notifications.
4. Ten requested languages plus catalog preservation for Turkish; right-to-left Arabic and Urdu; mobile/tablet/desktop layouts; group registration; comments with multiple photos; moderation; private image protection.
5. Live homepage and finder; staff portrait upload, publication with permission, signed-out access, revocation and persistence; school invitation-code changes with password confirmation.

Unit tests also exercise capacity races, mixed adult/child limits, ownership checks, CSRF, school isolation, upload validation and image deletion, saved-data persistence, safe migrations, and password reset using an isolated mailbox.

The Django deployment check passes with two optional HSTS warnings: include-subdomains and preload. These are not enabled automatically for a shared hosting domain.

## External verification limits

- Live password-reset email delivery cannot be established from a local test mailbox. The Vercel SMTP/provider settings and actual inbox delivery need a trusted provider check. No real email is sent by these tests.
- AI preference interpretation requires provider credentials. The filter-based finder works without them.
- The primary Vercel project is `school-choice-app-hrvb`. The separate `school-choice-app` project and pull-request previews have existing failures whose logs require Vercel account access. Check the primary production deployment after merging rather than treating a preview failure as a successful release.
- Actual events and sessions must be supplied and published by authorized staff/organizers. Empty listings do not represent invented availability. No payment collection is offered.

Verification applies to the tested release and the journeys listed above. Third-party delivery and future changes require their own checks.
