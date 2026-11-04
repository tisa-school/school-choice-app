from django.contrib import admin
from .models import School, Membership
@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display=['name','time_zone']
    fields=['name','time_zone']
    def has_add_permission(self,request): return False
@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display=['user','school','role','verified']
    list_filter=['school','role','verified']
    autocomplete_fields=['user']

from .models import Event
@admin.register(Event)
class EventAuditAdmin(admin.ModelAdmin):
    list_display=['title','school','listing_type','visibility','status','published_by']
    readonly_fields=['title','school','listing_type','visibility','status','published_by','published_at']
    fields=readonly_fields
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False
