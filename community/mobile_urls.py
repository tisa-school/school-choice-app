from django.urls import path
from . import mobile_api as api
urlpatterns=[
 path('capabilities/',api.capabilities),path('auth/login/',api.login),path('auth/signup/',api.signup),path('auth/logout/',api.logout),path('me/',api.me),
 path('events/',api.events),path('events/<int:pk>/',api.event_detail),path('events/<int:pk>/save/',api.save_event),path('events/<int:pk>/ticket/',api.ticket),
 path('public/events/<int:pk>/',api.public_event),path('schools/compare/',api.school_compare),path('schools/<int:pk>/',api.school_detail),path('schools/',api.schools),path('schools/<slug:slug>/save/',api.save_school),path('saved/',api.saved),path('family/',api.family),
 path('family/children/',api.child),path('family/children/<int:pk>/',api.child),path('family/requests/',api.participation),path('family/requests/<int:pk>/decision/',api.decision),
 path('family/calendar/',api.calendar),path('family/calendar/<int:pk>/',api.calendar),path('notifications/',api.inbox),path('notifications/<int:pk>/read/',api.read_notification),
 path('announcements/',api.announcements),path('reports/',api.report),path('push/device/',api.push_device),path('privacy/deletion-request/',api.deletion_request),
]
