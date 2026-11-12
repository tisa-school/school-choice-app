"""One destination list for the live pages and registration-free presentation."""
from .demo_access import access_for

ICONS={
'home':'M3 10 12 3l9 7v11h-6v-7H9v7H3Z',
'activities':'M12 3v18M3 12h18M5 5l14 14M19 5 5 19',
'schools':'m3 10 9-6 9 6v11H3ZM9 21v-7h6v7M8 10h.01M16 10h.01',
'saved':'M6 3h12v18l-6-4-6 4Z',
'family':'M4 21v-3a8 8 0 0 1 16 0v3M8 7a4 4 0 1 0 8 0 4 4 0 1 0-8 0',
'calendar':'M3 5h18v16H3ZM7 3v4M17 3v4M3 10h18M7 14h2M13 14h2',
'community':'M3 3h18v14H9l-6 4ZM7 8h10M7 12h6',
'finder':'M10 3a7 7 0 1 0 0 14 7 7 0 1 0 0-14M15 15l6 6',
'safety':'m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6ZM8 12l3 3 5-6',
'about':'M12 11v7M12 6v1M12 2a10 10 0 1 0 0 20 10 10 0 1 0 0-20',
'photos':'M3 6h4l2-3h6l2 3h4v15H3ZM8 13a4 4 0 1 0 8 0 4 4 0 1 0-8 0',
'workspace':'M3 5h18v16H3ZM3 10h18M9 10v11',
}

def navigation(request,member):
    # Existing tools are reached through their owning section or the role-aware account menu.
    path=request.path
    active='discover'
    if path.startswith(('/discover/activities/','/events/','/activities/','/experiences/','/finder/','/calendar/')):active='activities'
    elif path.startswith('/schools/'):active='schools'
    elif path.startswith(('/my-family/','/family/','/saved/','/collections/','/private/children/')):active='family'
    elif path.startswith(('/community/','/announcements/','/tickets/')):active='community'
    rows=[('discover','Discover','/','home'),('activities','Activities','/discover/activities/','activities'),('schools','Schools','/schools/','schools'),('family','My Family','/my-family/','family'),('community','Community','/community/','community')]
    return [dict(key=key,label=label,url=url,icon_path=ICONS[icon],demo_view='',required_role='',active=key==active) for key,label,url,icon in rows]
