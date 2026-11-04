# TK-ZONE ✦

A working, school-scoped events and community application. Django 5.2 LTS, Python 3.12+, SQLite, server-rendered semantic HTML, and progressive JavaScript. The six brand colors are shared CSS variables; Archivo Black and Inter are hosted locally under their included OFL licenses. No external frontend runtime, invented events, default accounts, invite codes, or statistics.

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
