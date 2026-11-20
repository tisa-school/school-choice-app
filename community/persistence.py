from django.contrib import messages
from .models import SaveReceipt


def record_saved_change(request, message):
    """Record a real write inside the caller's transaction; never infer it from HTTP 200."""
    if not request.user.is_authenticated:
        return None
    receipt, _ = SaveReceipt.objects.update_or_create(
        user=request.user, defaults={'action': str(message)[:120]}
    )
    return receipt


def receipt_payload(receipt):
    if receipt is None:
        return None
    return {'saved_at': receipt.saved_at.isoformat(), 'action': receipt.action}


def saved_success(request, message):
    """Called after a successful database write, never for validation failures or auth."""
    receipt = record_saved_change(request, message)
    messages.success(request, message)
    return receipt
