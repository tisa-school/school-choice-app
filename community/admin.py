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

from .models import Feedback
@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display=['kind','status','created_at','school','listing']
    list_filter=['kind','status','school']
    readonly_fields=['kind','message','listing','school','submitted_by','created_at','reviewed_by','reviewed_at']
    fields=['kind','message','listing','school','submitted_by','created_at','status','review_note','reviewed_by','reviewed_at']
    def has_module_permission(self,request): return request.user.is_superuser
    def has_view_permission(self,request,obj=None): return request.user.is_superuser
    def has_change_permission(self,request,obj=None): return request.user.is_superuser
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return request.user.is_superuser
    def save_model(self,request,obj,form,change):
        from django.utils import timezone
        obj.reviewed_by=request.user;obj.reviewed_at=timezone.now();super().save_model(request,obj,form,change)
