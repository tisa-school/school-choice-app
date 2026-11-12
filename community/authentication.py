"""Authenticate existing identities without granting or inferring any role."""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.core.exceptions import PermissionDenied

class ExistingIdentityBackend(ModelBackend):
    def authenticate(self,request,username=None,password=None,**kwargs):
        User=get_user_model();identity=(username or kwargs.get(User.USERNAME_FIELD) or '').strip()
        if password is None:return None
        candidates=list(User._default_manager.filter(Q(username__iexact=identity)|Q(email__iexact=identity))[:2]) if identity else []
        if len(candidates)>1:raise PermissionDenied()
        if len(candidates)!=1:
            User().set_password(password)
            return None
        user=candidates[0]
        if user.check_password(password) and self.user_can_authenticate(user):return user
        return None
