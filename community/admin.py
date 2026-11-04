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
