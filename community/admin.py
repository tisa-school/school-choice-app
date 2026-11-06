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

from .models import TeamPhoto,EventExperience,ExperiencePhoto,ExperienceReport,FamilyBooking
from .community_forms import TeamPhotoForm

@admin.register(TeamPhoto)
class TeamPhotoAdmin(admin.ModelAdmin):
    form=TeamPhotoForm
    list_display=['display_name','school','is_student','visibility','sharing_permission','guardian_consent']
    list_filter=['school','visibility','is_student']
    def has_module_permission(self,request):return request.user.is_superuser
    def has_view_permission(self,request,obj=None):return request.user.is_superuser
    def has_add_permission(self,request):return request.user.is_superuser
    def has_change_permission(self,request,obj=None):return request.user.is_superuser
    def has_delete_permission(self,request,obj=None):return request.user.is_superuser
    def save_model(self,request,obj,form,change):
        if not change:obj.uploaded_by=request.user
        super().save_model(request,obj,form,change)

@admin.register(EventExperience,ExperiencePhoto,ExperienceReport,FamilyBooking)
class CommunityAuditAdmin(admin.ModelAdmin):
    def has_module_permission(self,request):return request.user.is_superuser
    def has_view_permission(self,request,obj=None):return request.user.is_superuser
    # Use the application actions to enforce capacity, moderation and upload validation.
    def has_change_permission(self,request,obj=None):return False
    def has_add_permission(self,request):return False
    def has_delete_permission(self,request,obj=None):return False
