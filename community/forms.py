from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from zoneinfo import ZoneInfo
from .models import Event, Announcement, Collection

class SignupForm(UserCreationForm):
    name=forms.CharField(max_length=100,label='Your name')
    email=forms.EmailField(max_length=150)
    class Meta:
        model=User
        fields=['name','email','password1','password2']
    def save(self,commit=True):
        user=super().save(False)
        user.username=self.cleaned_data['email'].lower()
        user.email=user.username
        user.first_name=self.cleaned_data['name']
        if commit: user.save()
        return user
class EmailLoginForm(AuthenticationForm):
    username=forms.EmailField(label='Email')
    def clean_username(self): return self.cleaned_data['username'].strip().lower()
class JoinForm(forms.Form):
    school=forms.ModelChoiceField(queryset=None,empty_label='Choose your school')
    code=forms.CharField(label='School invite code',widget=forms.PasswordInput)
    def __init__(self,*args,**kwargs):
        from .models import School
        super().__init__(*args,**kwargs)
        self.fields['school'].queryset=School.objects.order_by('name')
class ImageValidationMixin:
    def clean_image(self):
        image=self.cleaned_data.get('image')
        if image and hasattr(image,'size'):
            if image.size>settings.MAX_IMAGE_BYTES: raise ValidationError(f'Images must be {settings.MAX_IMAGE_BYTES // (1024*1024)} MB or smaller.')
            if getattr(image,'content_type',None) not in ('image/jpeg','image/png','image/webp'):
                raise ValidationError('Choose a JPEG, PNG, or WebP image.')
            from PIL import Image
            try:
                picture=Image.open(image)
                if picture.format not in ('JPEG','PNG','WEBP') or picture.width*picture.height>24000000: raise ValueError()
                picture.verify()
                image.seek(0)
            except Exception: raise ValidationError('Choose a valid image up to 24 megapixels.')
        return image
class EventForm(ImageValidationMixin,forms.ModelForm):
    class Meta:
        model=Event
        fields=['title','category','image','start_at','end_at','venue','description','organizer','ticket_requests_enabled','capacity','price_text','requests_close_at','status']
        widgets={k:forms.DateTimeInput(format='%Y-%m-%dT%H:%M',attrs={'type':'datetime-local'}) for k in ['start_at','end_at','requests_close_at']}
        labels={'capacity':'Capacity (leave empty for unlimited)','price_text':'Price information (optional)','status':'Publication status'}
    def clean(self):
        data=super().clean()
        start,end=data.get('start_at'),data.get('end_at')
        if start and end and end<=start: self.add_error('end_at','End time must be after start time.')
        if data.get('requests_close_at') and start and data['requests_close_at']>start: self.add_error('requests_close_at','Requests must close by the event start.')
        capacity=data.get('capacity')
        if capacity==0: self.add_error('capacity','Capacity must be at least one, or left empty.')
        if self.instance.pk and capacity is not None and capacity<self.instance.requests.filter(status='approved').count(): self.add_error('capacity','Capacity cannot be lower than the number of approved tickets.')
        if data.get('status')=='published' and start and start<=timezone.now(): self.add_error('start_at','Publish an event with a future start time.')
        return data
class AnnouncementForm(ImageValidationMixin,forms.ModelForm):
    class Meta:
        model=Announcement
        fields=['title','body','image','status','scheduled_for','is_pinned']
        widgets={'scheduled_for':forms.DateTimeInput(format='%Y-%m-%dT%H:%M',attrs={'type':'datetime-local'})}
    def clean(self):
        data=super().clean()
        if data.get('status')=='scheduled' and (not data.get('scheduled_for') or data['scheduled_for']<=timezone.now()): self.add_error('scheduled_for','Choose a future publication date in your school time zone.')
        return data
class CollectionForm(forms.ModelForm):
    class Meta:
        model=Collection
        fields=['name','cover_style']
class ProfileForm(forms.ModelForm):
    class Meta:
        model=User
        fields=['first_name','last_name']
        labels={'first_name':'Display name'}
