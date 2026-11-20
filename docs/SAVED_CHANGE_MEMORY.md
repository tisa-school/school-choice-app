# Saved-change memory

Real account content stays in the application's existing persistent database after a successful Save, refresh and new sign-in. Vercel continues to use PostgreSQL and private database-backed image storage. There is no new database, migration, browser storage of private photos, Gmail requirement or production-data reset.

## Confirmations

- The existing Saved to database banner retains the owner's last confirmed action and server timestamp.
- Photos, community contributions/reviews, administrator publication/settings/media actions, school shortlists and saved activities now use the same receipt mechanism.
- Photo and bookmark AJAX responses include a private `save_receipt` with `saved_at` and `action`. The banner refreshes from that server receipt, not the browser clock.
- During a request the banner says Saving changes. A failed request says the change was not saved, while retaining the previous confirmed timestamp and details.
- Photo bytes, profile relationship, audit and receipt commit together. A failed receipt write rolls back the photo replacement; it cannot report success for a partial operation.
- Ordinary successful form submissions also update the saved receipt. Validation failures, previews, sign-in and page visits do not claim a completed content save.

Click Save/Submit to commit a form. Unsubmitted typing is not automatically stored. Device-only accessibility preferences and explicitly fictional demo actions keep their existing separate storage behaviour; they are not represented as production database saves. The chat assistant remains stateless.

Persistence depends on retaining the same production database. A code deployment does not reset that database; deleting or replacing the active Neon database is a different action that this UI cannot undo.

## Verification

- 299 backend tests passed, including private receipts, validation failures, rollback, new sign-in persistence and photo-byte/receipt atomicity.
- Eight Chromium browser workflows passed, including photo save/delete, successful and failed save feedback, refresh, login, saved schools/activities and family calendar persistence.
- Five existing JavaScript test scripts and modified-script syntax checks passed.
- Django checks, migration-drift validation and the isolated Vercel preview build script passed. This is not verification of a hosted deployment or production database connection.

The restored 83a5d9b homepage and sidebar are unchanged.
