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
    authenticated=request.user.is_authenticated
    staff=bool(member and member.role=='staff' and member.verified)
    organizer=bool(member and member.role=='organizer' and member.verified)
    access=access_for(request.user)
    items=[]
    def add(key,label,url,icon='workspace',demo_view='',required_role=''):
        if not url.startswith('/demo/'):demo_view=''
        items.append(dict(key=key,label=label,url=url,icon_path=ICONS[icon],demo_view=demo_view,required_role=required_role,active=False))
    add('home','Home','/','home','home')
    add('activities','Activities','/discover/activities/','activities','events')
    add('schools','Find schools','/schools/','schools')
    add('saved','Saved','/saved/','saved')
    add('family','Family workspace','/family/' if authenticated else '/demo/family/','family','family')
    add('community','Live school community','/community/','community')
    add('finder','Activity Finder','/finder/','finder')
    add('calendar','Calendar','/calendar/','calendar')
    add('demo-catalogue','Demo catalogue','/demo/events/','activities','events')
    add('child','My zone','/demo/child/','family','child')
    add('crews','Crews','/demo/crews/','community','crews')
    add('demo-calendar','Demo family calendar','/demo/calendar/','calendar','calendar')
    add('presentation','Presentation demo','/demo/','workspace')
    add('safety','Safety Centre','/demo/safety/','safety','safety')
    add('feedback','Share Feedback','/feedback/','community')
    if member and member.role!='organizer':
        add('announcements','School announcements','/announcements/','community')
        if member.role=='student':add('tickets','My school tickets','/tickets/','saved')
    elif authenticated and not member:add('join','Join your school','/join/','schools')
    if staff:
        for key,label,url in [('staff','Overview & listings','/staff/'),('school-profile','School directory profile','/staff/school-profile/'),('approvals','Participation requests','/staff/requests/'),('studio','Announcement studio','/staff/announcements/'),('feedback-inbox','Listing reports & feedback','/staff/feedback/'),('applications','Organizer applications','/staff/organizers/'),('moderation','Content moderation','/staff/content/')]:add(key,label,url)
    if organizer:add('organizer','Organiser studio','/organizer/','workspace','organizer','organizer')
    elif not authenticated:add('organizer','Organiser studio','/demo/organizer/','workspace','organizer','organizer')
    if 'admin' in access['roles']:add('admin','Demo moderation','/demo/admin/','workspace','admin','admin')
    if authenticated:add('notifications','Notifications','/notifications/','community')
    add('account','Profile & settings' if authenticated else 'Account access','/profile/' if authenticated else '/accounts/login/','family')
    add('about','About Us','/about/','about','about')
    add('photos','Team photos','/team/photos/','photos')
    path=request.path
    mappings=[('/staff/school-profile/','school-profile'),('/staff/requests/','approvals'),('/staff/announcements/','studio'),('/staff/feedback/','feedback-inbox'),('/staff/organizers/','applications'),('/staff/content/','moderation'),('/staff/','staff'),('/organizer/','organizer'),('/schools/','schools'),('/saved/','saved'),('/collections/','saved'),('/discover/activities/','activities'),('/activities/','activities'),('/events/','activities'),('/family/','family'),('/community/','community'),('/finder/','finder'),('/calendar/','calendar'),('/announcements/','announcements'),('/tickets/','tickets'),('/join/','join'),('/feedback/','feedback'),('/about/','about'),('/team/','photos'),('/notifications/','notifications'),('/profile/','account'),('/accounts/','account')]
    active=next((key for prefix,key in mappings if path.startswith(prefix)),'home')
    if path.startswith('/demo/'):
        section=path.split('/')[2] if len(path.split('/'))>2 else ''
        active={'':'presentation','events':'demo-catalogue','activities':'demo-catalogue','detail':'demo-catalogue','family':'family','calendar':'demo-calendar','creator':'organizer','onboarding':'child','finder':'finder'}.get(section,section)
    if active not in {item['key'] for item in items}:active='home'
    for item in items:item['active']=item['key']==active
    return items
