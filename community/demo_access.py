"""Signed-in demo roles follow accounts. Guests may explicitly explore fictional roles."""
from .discovery import membership


def access_for(user):
    if not user.is_authenticated:
        return {'roles':['child','parent','organizer','admin'], 'initial':'child', 'account_bound':False}
    member = membership(user)
    if user.is_superuser or (member and member.role == 'staff' and member.verified):
        role = 'admin'
    elif member and member.role == 'organizer' and member.verified:
        role = 'organizer'
    elif member and member.role == 'student':
        role = 'child'
    else:
        role = 'parent'
    return {'roles':[role], 'initial':role, 'account_bound':True}


def allows(user, role):
    return role in access_for(user)['roles']
