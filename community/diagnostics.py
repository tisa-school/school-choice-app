"""Deployment readiness exposes no hosts, credentials, account data or key values."""
from django.http import JsonResponse
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.views.decorators.http import require_GET
from django.conf import settings
from django.shortcuts import render
from .management_views import administrator

@require_GET
def health(request):
    try:
        connection.ensure_connection()
        executor=MigrationExecutor(connection)
        ready=not executor.migration_plan(executor.loader.graph.leaf_nodes())
    except Exception:ready=False
    response=JsonResponse({'status':'ok' if ready else 'unavailable'},status=200 if ready else 503)
    response['Cache-Control']='no-store';return response

@administrator
def deployment_diagnostics(request):
    from django.core.files.storage import default_storage
    executor=MigrationExecutor(connection)
    pending=executor.migration_plan(executor.loader.graph.leaf_nodes())
    email_backend=settings.EMAIL_BACKEND
    recovery_configured=email_backend not in ['django.core.mail.backends.filebased.EmailBackend','django.core.mail.backends.console.EmailBackend','django.core.mail.backends.locmem.EmailBackend','django.core.mail.backends.dummy.EmailBackend']
    return render(request,'management/diagnostics.html',{'diagnostic_rows':[
        ('Application database',connection.vendor),('Pending migrations',str(len(pending))),('Private media backend',default_storage.__class__.__name__),('Recovery email delivery','Configured; delivery needs a real test' if recovery_configured else 'Not configured for actual email delivery'),('Authentication','Existing username or email; no automatic role grants'),('Administrator authority','Super administrator' if request.user.is_superuser else 'Verified school administrator'),('AI provider','Configured' if settings.ANTHROPIC_API_KEY else 'Not configured')
    ]})
