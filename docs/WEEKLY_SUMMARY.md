# Parent weekly summary

The demo Parent inbox automatically shows current-week request and approval counts, a suitable upcoming fictional activity, and optional AI commentary. Counts are deterministic application data. AI never chooses the counts or the suggested activity.

New demo requests carry a timestamp in the saved action journal. The week runs Monday–Sunday in Europe/Lisbon. Duplicate requests for an activity do not inflate the activity count; cancellations and declines are not counted as current approvals. Existing checkpoints without request dates are preserved and clearly labelled **this demo session** rather than inventing dates.

Suggested activities must be published/approved, upcoming, within the child's age range and interests, English-friendly for the fictional English-speaking Emma, not already requested, within demo capacity, and free of approved-plan time conflicts. Parent weekend preferences are respected. No eligible suggestion produces an explicit empty state rather than an invented listing. Date/title links come directly from the fictional catalogue.

The live `/family/` workspace also receives an owner-scoped weekly overview of individual participation records. Counts use records created this calendar week; parent-approved means organiser-pending or confirmed, not guaranteed admission. Anonymous AI commentary is loaded through an authenticated, parent-only POST endpoint which calculates its own counts and ignores any client-supplied statistics. Group bookings are not included in this explicitly labelled individual-request overview. Existing family functionality is preserved.

Claude receives only requested count, approved count, period label, and language—no child name, age, identifiers, account details, school, event title or private records. It adds one short friendly sentence; application facts and recommendation links remain authoritative. Successful anonymous commentary is cached for fifteen minutes, identical in-flight demo requests are deduplicated, and normal CSRF/rate protections apply. An AI badge appears only after a genuine successful response. Missing keys/credits, timeouts or invalid output retain the factual overview.

Summaries refresh on opening the inbox and after demo decisions, requests or reset. Refresh recovery preserves timestamps and decisions. No emails, scheduled jobs, bookings or external notifications are created. This is an on-screen summary, not an emailed weekly digest.

Tests cover Lisbon week boundaries, zero counts, old checkpoints, current decisions, conflict-free recommendations, no future suggestions after catalogue expiry, reset/refresh, real-parent scoping, forged client counts, anonymous provider payloads, missing credits, invalid numeric AI claims and browser fallback labels. API tests use mocked responses and incur no provider charges.

[Implemented weekly summary card](screenshots/weekly-summary.png) — captured from the tested two-request, one-approval demo journey.
