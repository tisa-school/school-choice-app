from django.contrib import messages
from .models import SaveReceipt

def saved_success(request, message):
    """Called after a successful database write, never for validation failures or auth."""
    if request.user.is_authenticated:
        SaveReceipt.objects.update_or_create(user=request.user, defaults={'action':str(message)[:120]})
    messages.success(request, message)
