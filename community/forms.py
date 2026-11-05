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
        if image and hasattr(image,'content_type'):
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
        fields=['title','listing_type','visibility','identity_verified','category','image','start_at','end_at','venue','description','organizer','address','contact_name','contact_phone','contact_website','contact_public','min_age','max_age','languages','area','price_amount','supervision','accessibility','cancellation_policy','time_zone','ticket_requests_enabled','capacity','price_text','requests_close_at','status']
        widgets={**{k:forms.DateTimeInput(format='%Y-%m-%dT%H:%M',attrs={'type':'datetime-local'}) for k in ['start_at','end_at','requests_close_at']},'image':forms.FileInput(attrs={'accept':'image/jpeg,image/png,image/webp'})}
        labels={'identity_verified':'Organizer identity checked by staff (not a safety guarantee)','start_at':'Start at / first activity date','capacity':'Capacity (leave empty for unlimited)','price_text':'Price information (optional)','status':'Publication status'}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        zone=self.data.get('time_zone') if self.is_bound else self.instance.time_zone
        if zone:
            try: timezone.activate(ZoneInfo(zone))
            except (ValueError,KeyError): pass
        for name in ['listing_type','visibility','time_zone']:
            if name in self.fields: self.fields[name].required=False
        if 'status' in self.fields: self.fields['status'].choices=[('draft','Draft'),('published','Published')]
    def clean(self):
        data=super().clean()
        for name,default in [('listing_type','event'),('visibility','school'),('time_zone','Europe/Lisbon')]:
            if not data.get(name): data[name]=getattr(self.instance,name,None) or default
        try: ZoneInfo(data['time_zone'])
        except (ValueError,KeyError): self.add_error('time_zone','Enter a valid IANA time zone, such as Europe/Lisbon.')
        if data.get('languages'):
            try: data['languages']=normalize_languages(data['languages'])
            except ValidationError as error: self.add_error('languages',error)
        low,high=data.get('min_age'),data.get('max_age')
        if (low is None)!=(high is None) or (low is not None and (low>high or high>17)):
            self.add_error('max_age','Provide both age bounds, with minimum no higher than maximum, up to 17.')
        if data.get('price_amount') is not None and data['price_amount']<0: self.add_error('price_amount','Price cannot be negative.')
        for field in ['contact_website']:
            if data.get(field) and not data[field].startswith(('https://','http://')): self.add_error(field,'Use an HTTPS or HTTP website address.')
        if data.get('contact_phone'):
            import re
            if not re.fullmatch(r'[+0-9 ()\-x.]{6,40}',data['contact_phone']): self.add_error('contact_phone','Use a valid public business phone number.')
        if data.get('contact_public') and (not data.get('contact_name') or not (data.get('contact_phone') or data.get('contact_website'))): self.add_error('contact_public','Provide a contact name and a business phone or website before sharing contact details.')
        start,end=data.get('start_at'),data.get('end_at')
        if start and end and end<=start: self.add_error('end_at','End time must be after start time.')
        if data.get('requests_close_at') and start and data['requests_close_at']>start: self.add_error('requests_close_at','Requests must close by the event start.')
        capacity=data.get('capacity')
        if capacity==0: self.add_error('capacity','Capacity must be at least one, or left empty.')
        if self.instance.pk and capacity is not None and capacity<(self.instance.requests.filter(status='approved').count()+self.instance.participations.filter(status='confirmed',session__isnull=True).count()): self.add_error('capacity','Capacity cannot be lower than the number of approved tickets.')
        if self.instance.pk and data.get('listing_type')!=self.instance.listing_type and (self.instance.requests.exists() or self.instance.participations.exists() or self.instance.sessions.exists()): self.add_error('listing_type','A listing with requests or sessions cannot change type.')
        if data.get('status')=='published' and start and start<=timezone.now(): self.add_error('start_at','Publish an event with a future start time.')
        return data
class AnnouncementForm(ImageValidationMixin,forms.ModelForm):
    class Meta:
        model=Announcement
        fields=['title','body','image','status','scheduled_for','is_pinned']
        widgets={'scheduled_for':forms.DateTimeInput(format='%Y-%m-%dT%H:%M',attrs={'type':'datetime-local'}),'image':forms.FileInput(attrs={'accept':'image/jpeg,image/png,image/webp'})}
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

from .models import ChildProfile, ActivitySession, FamilyPlan
from .discovery import LANGUAGES

class ParentSetupForm(forms.Form):
    guardian_consent = forms.BooleanField(label='I am an adult parent or legal guardian and will manage these child profiles and participation decisions.')

class ChildProfileForm(forms.ModelForm):
    class Meta:
        model=ChildProfile
        fields=['nickname','age_band','interests','languages']
        labels={'languages':'Preferred languages (codes, for example en, pt)'}
    def clean_languages(self): return normalize_languages(self.cleaned_data.get('languages',''))

class SessionForm(forms.ModelForm):
    class Meta:
        model=ActivitySession
        fields=['start_at','end_at','capacity','venue','is_cancelled']
        widgets={k:forms.DateTimeInput(format='%Y-%m-%dT%H:%M',attrs={'type':'datetime-local'}) for k in ['start_at','end_at']}
        labels={'is_cancelled':'Cancel this session and its active participation requests'}
    def clean(self):
        data=super().clean()
        if data.get('start_at') and data.get('end_at') and data['end_at']<=data['start_at']: self.add_error('end_at','End time must follow the start.')
        if data.get('capacity')==0: self.add_error('capacity','Use at least one place, or leave empty for unlimited.')
        if self.instance.pk and data.get('capacity') is not None and data['capacity']<self.instance.participations.filter(status='confirmed').count(): self.add_error('capacity','Capacity cannot fall below confirmed places.')
        return data

def normalize_languages(value):
    codes=[item.strip().lower() for item in value.split(',') if item.strip()]
    if any(code not in dict(LANGUAGES) for code in codes): raise ValidationError('Use supported language codes: en, pt, fr, es, de, it, nl.')
    return ','.join(dict.fromkeys(codes))

class OrganizerSubmissionForm(EventForm):
    class Meta(EventForm.Meta):
        fields=[f for f in EventForm.Meta.fields if f not in ['status','identity_verified']]
    def __init__(self,*args,draft=False,**kwargs):
        self.draft=draft
        super().__init__(*args,**kwargs)
        if draft:
            for name in ['venue','description']: self.fields[name].required=False
    def clean(self):
        data=super().clean()
        if not self.draft and data.get('start_at') and data['start_at']<=timezone.now(): self.add_error('start_at','Choose a future date before submitting for review.')
        return data

from .models import OrganizerApplication
class OrganizerApplicationForm(forms.ModelForm):
    adult_consent=forms.BooleanField(label='I am an adult authorized to represent this organization. I understand that staff must review my application before I can submit listings.')
    class Meta:
        model=OrganizerApplication
        fields=['school','organization','contact_name','phone','website','description']
        labels={'school':'School reviewing your application','phone':'Business phone','description':'Tell us about your organization and the supervised activities you offer'}
    def clean_website(self):
        website=self.cleaned_data.get('website','')
        if website and not website.startswith(('https://','http://')): raise ValidationError('Use an HTTPS or HTTP website address.')
        return website
    def clean_phone(self):
        import re
        phone=self.cleaned_data['phone']
        if not re.fullmatch(r'[+0-9 ()\-x.]{6,40}',phone): raise ValidationError('Use a valid business phone number.')
        return phone
