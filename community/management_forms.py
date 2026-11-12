from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .forms import LocalizedFieldsMixin,EventForm,ChildProfileForm
from .directory_forms import SchoolProfileForm
from .community_forms import clean_photo
from .models import ExperienceListing,SchoolMedia,SiteConfiguration,School,PrivateFamilyEvent

class ManagedUserForm(LocalizedFieldsMixin,forms.ModelForm):
    current_password=forms.CharField(label='Confirm your password',widget=forms.PasswordInput,required=False)
    class Meta:model=User;fields=['first_name','last_name','email','is_active']
    def __init__(self,*args,actor,**kwargs):
        self.actor=actor;super().__init__(*args,**kwargs)
        if not actor.is_superuser:
            self.fields.pop('email');self.fields.pop('is_active');self.fields.pop('current_password')
    def clean(self):
        data=super().clean()
        if self.actor.is_superuser and any(k in self.changed_data for k in ['email','is_active']):
            if not self.actor.check_password(data.get('current_password','')):raise ValidationError('Confirm your current password before changing account access.')
            if self.instance.pk==self.actor.pk and data.get('is_active') is False:raise ValidationError('You cannot deactivate your own administrator account.')
            if data.get('email') and User.objects.exclude(pk=self.instance.pk).filter(email__iexact=data['email']).exists():self.add_error('email','This account change cannot be completed.')
        return data

class ManagedEventForm(EventForm):
    school=forms.ModelChoiceField(queryset=School.objects.all(),label='School context')
    def __init__(self,*args,actor,member,**kwargs):
        super().__init__(*args,**kwargs)
        if not actor.is_superuser:self.fields['school'].queryset=School.objects.filter(pk=member.school_id)
        if self.instance.pk:self.initial['school']=self.instance.school_id
        elif member:self.initial['school']=member.school_id
    def save(self,commit=True):
        self.instance.school=self.cleaned_data['school']
        return super().save(commit)

class ExperienceForm(LocalizedFieldsMixin,forms.ModelForm):
    class Meta:
        model=ExperienceListing
        exclude=['slug','created_by','school','updated_at']
        widgets={'last_verified':forms.DateInput(attrs={'type':'date'})}

class SchoolMediaForm(LocalizedFieldsMixin,forms.ModelForm):
    class Meta:
        model=SchoolMedia;exclude=['school_profile','uploaded_by','created_at']
        widgets={'image':forms.FileInput(attrs={'accept':'image/jpeg,image/png,image/webp'})}
    def clean_image(self):
        image=self.cleaned_data.get('image');return clean_photo(image) if image and hasattr(image,'content_type') else image

class SiteConfigurationForm(LocalizedFieldsMixin,forms.ModelForm):
    class Meta:model=SiteConfiguration;exclude=['updated_at']

class PrivateFamilyEventForm(LocalizedFieldsMixin,forms.ModelForm):
    class Meta:
        model=PrivateFamilyEvent;fields=['title','start_at','end_at','note']
        widgets={k:forms.DateTimeInput(format='%Y-%m-%dT%H:%M',attrs={'type':'datetime-local'}) for k in ['start_at','end_at']}

class PrivateChildForm(ChildProfileForm):
    photo=forms.FileField(label='Private profile photo',required=False,widget=forms.FileInput(attrs={'accept':'image/jpeg,image/png,image/webp','data-crop-file':''}))
    crop_x=forms.FloatField(label='Horizontal position',min_value=0,max_value=1,initial=.5,required=False,widget=forms.NumberInput(attrs={'type':'range','step':'.01','data-crop-axis':'x'}))
    crop_y=forms.FloatField(label='Vertical position',min_value=0,max_value=1,initial=.5,required=False,widget=forms.NumberInput(attrs={'type':'range','step':'.01','data-crop-axis':'y'}))
    crop_zoom=forms.FloatField(label='Zoom',min_value=1,max_value=3,initial=1,required=False,widget=forms.NumberInput(attrs={'type':'range','step':'.05','data-crop-axis':'zoom'}))
    photo_permission=forms.BooleanField(label='I am authorised to manage this private child photograph.',required=False)
    remove_photo=forms.BooleanField(label='Remove existing photo',required=False)
    class Meta(ChildProfileForm.Meta):
        fields=['nickname','age_band','interests','languages','preferred_activity_types','photo']
    def clean_photo(self):
        photo=self.cleaned_data.get('photo');return clean_photo(photo) if photo and hasattr(photo,'content_type') else photo
    def clean(self):
        data=super().clean()
        if self.files.get('photo') and not data.get('photo_permission'):self.add_error('photo_permission','Confirm your authority before uploading a child photo.')
        if data.get('remove_photo') and self.files.get('photo'):self.add_error('remove_photo','Choose either a replacement photo or removal.')
        if not self.files.get('photo'):data['photo']='' if data.get('remove_photo') else self.instance.photo
        elif not self.errors:
            from .community_forms import crop_photo
            data['photo']=crop_photo(data['photo'],data.get('crop_x') if data.get('crop_x') is not None else .5,data.get('crop_y') if data.get('crop_y') is not None else .5,data.get('crop_zoom') or 1)
        return data

class ReportReviewForm(LocalizedFieldsMixin,forms.ModelForm):
    class Meta:
        from .models import Feedback
        model=Feedback;fields=['status','review_note']

class OrganizerReviewForm(LocalizedFieldsMixin,forms.Form):
    status=forms.ChoiceField(label='Decision',choices=[('approved','Approve'),('declined','Decline')])
    note=forms.CharField(label='Decision note',max_length=500,required=False,widget=forms.Textarea)
