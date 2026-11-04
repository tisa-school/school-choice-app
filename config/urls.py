from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path
from community import views as v
from community.forms import EmailLoginForm
urlpatterns=[
path('admin/',admin.site.urls),path('',v.home,name='home'),path('welcome/',v.welcome,name='welcome'),
path('accounts/signup/',v.signup,name='signup'),path('accounts/login/',auth.LoginView.as_view(authentication_form=EmailLoginForm),name='login'),path('accounts/logout/',auth.LogoutView.as_view(),name='logout'),
path('accounts/password-reset/',auth.PasswordResetView.as_view(),name='password_reset'),path('accounts/password-reset/done/',auth.PasswordResetDoneView.as_view(),name='password_reset_done'),path('accounts/reset/<uidb64>/<token>/',auth.PasswordResetConfirmView.as_view(),name='password_reset_confirm'),path('accounts/reset/done/',auth.PasswordResetCompleteView.as_view(),name='password_reset_complete'),
path('accounts/password-change/',auth.PasswordChangeView.as_view(success_url='/profile/'),name='password_change'),path('join/',v.join,name='join'),
path('events/',v.home,name='events'),path('events/<int:pk>/',v.detail,name='detail'),path('events/<int:pk>/request/',v.ticket_request,name='ticket_request'),path('events/<int:pk>/save/',v.save_event,name='save_event'),
path('tickets/',v.tickets,name='tickets'),path('tickets/<int:pk>/cancel/',v.cancel_ticket,name='cancel_ticket'),
path('saved/',v.saved,name='saved'),path('collections/new/',v.collection_edit,name='collection_new'),path('collections/<int:pk>/',v.collection_edit,name='collection_edit'),path('collections/<int:pk>/action/',v.collection_action,name='collection_action'),
path('announcements/',v.announcements,name='announcements'),path('notifications/',v.notifications,name='notifications'),path('notifications/<int:pk>/read/',v.read_notification,name='read_notification'),path('profile/',v.profile,name='profile'),
path('staff/',v.staff_home,name='staff'),path('staff/events/new/',v.event_edit,name='event_new'),path('staff/events/<int:pk>/',v.event_edit,name='event_edit'),path('staff/requests/',v.approval_center,name='approvals'),path('staff/requests/<int:pk>/decision/',v.decision,name='decision'),
path('staff/announcements/',v.studio,name='studio'),path('staff/announcements/new/',v.announcement_edit,name='announcement_new'),path('staff/announcements/<int:pk>/',v.announcement_edit,name='announcement_edit'),path('media/<str:kind>/<int:pk>/',v.media,name='private_media')]
