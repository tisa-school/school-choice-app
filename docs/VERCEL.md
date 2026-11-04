# Deploy TK-ZONE from GitHub to Vercel

Target Vercel team: **tisa9**. Source repository: **tisa-school/school-choice-app**, branch **main**.

## Connect the accounts

1. Open https://vercel.com/tisa9 and select **Add New → Project**.
2. Connect GitHub, authorize the Vercel GitHub App for `tisa-school/school-choice-app`, and import that repository. An organization owner may need to approve installation.
3. Keep the root directory at the repository root and framework preset **Django**. `vercel.json` supplies the build command. Vercel detects `manage.py` and `config/wsgi.py`; no Node frontend or deprecated Python builder is needed.
4. In the project settings, set the production branch to `main`.

Once linked, pushes to `main` trigger production deployments and pull requests can create previews. The GitHub checks exercise PostgreSQL, authorization, uploads, and concurrent capacity decisions. Vercel account linking and actual deployments require access to the target team; they cannot be activated by committing configuration alone.

## Persistent production data

Vercel's function filesystem is ephemeral. The app refuses to run there with SQLite or development debug mode. Add a managed PostgreSQL integration (for example Neon through the Vercel Marketplace), review its plan, and provide its pooled connection string as `DATABASE_URL`. No database or paid subscription is created by this repository.

School records, accounts, sessions, ticket requests, and small **private image uploads** persist in PostgreSQL. Private images are read through the existing school-authorized media route, never public bucket URLs. On Vercel images are limited to 3 MB to remain below function payload limits. Back up the database. This is intended for modest school content; large media libraries should move to separately reviewed private object storage.

## Vercel environment variables

Set these in the Vercel project's **Settings → Environment Variables**, securely, before deploying. Never put their values into Git or chat.

| Variable | Production value |
|---|---|
| `DJANGO_SECRET_KEY` | A newly generated persistent random signing secret, at least 50 characters |
| `DATABASE_URL` | Managed PostgreSQL connection string; TLS is required on Vercel |
| `DJANGO_ALLOWED_HOSTS` | Your exact production hostname; comma-separated for more than one |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | The corresponding full HTTPS origin(s), comma-separated |
| `DJANGO_EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | Your real SMTP provider hostname |
| `EMAIL_PORT` | SMTP STARTTLS port, typically `587` |
| `EMAIL_HOST_USER` | SMTP username supplied by your provider |
| `EMAIL_HOST_PASSWORD` | SMTP provider credential |
| `DEFAULT_FROM_EMAIL` | A verified sender address at your email provider |

`VERCEL`, `VERCEL_ENV`, `VERCEL_URL`, and `VERCEL_PROJECT_PRODUCTION_URL` are provided by Vercel; do not invent them. The exact deployment and project production hostnames are accepted automatically. Add custom domains to the allowed-host and CSRF lists. `DJANGO_DEBUG` defaults to `0` on Vercel; setting it to `1` causes startup to fail. The app trusts the forwarded HTTPS header only when running on Vercel.

For **isolated previews**, use a separate preview PostgreSQL database and signing secret. Do not expose production data to pull-request code. Production builds apply migrations automatically. Preview builds intentionally do not migrate a shared database: initialize the preview database explicitly using `python manage.py migrate --noinput` in a trusted environment with that preview `DATABASE_URL`. For previews with no real recovery email, explicitly set `DJANGO_EMAIL_BACKEND=django.core.mail.backends.dummy.EmailBackend`; this sends no email. Production needs the real SMTP configuration for password recovery.

## First deployment and real school setup

The production build runs Django checks, collects static files, and applies schema migrations; it never seeds school data or creates accounts. WhiteNoise and Vercel's Django integration serve the locally hosted CSS, JavaScript, and fonts. Failed migrations must be corrected before a deployment is considered ready.

After deployment:

1. Verify the welcome and signup pages, then register the real staff contact through signup.
2. In a trusted local/cloud shell with the **production PostgreSQL `DATABASE_URL`**, run `python manage.py configure_school --name '<real school>' --timezone Europe/Lisbon --staff-email '<registered email>'`. It privately prompts for a school invite code and grants verified school staff membership. Use the school's actual time zone.
3. Privately share the invite code with students. Do not paste it into Vercel settings, URLs, or the repository.
4. Verify staff event creation, a student request, staff approval, accurate wallet status, private images, and password recovery with the actual deployed services. These live-service checks remain necessary even after local tests pass.

## Scheduled announcements

Vercel functions cannot run the persistent `--watch` worker. Due announcements still publish transactionally when a school member opens the app. For precise background publication, run `python manage.py publish_scheduled` every minute on a trusted external scheduler with access to the same managed database. The command is idempotent. A cron service and any associated plan must be configured separately; none is silently created.

## Verification before merge/deploy

```sh
python manage.py check
python manage.py collectstatic --noinput
python manage.py test community.tests --noinput
```

Run those with a disposable PostgreSQL database to exercise the production row locks. The same suite also supports SQLite for local development. CI uses an isolated PostgreSQL service with test-only credentials, unrelated to production.
