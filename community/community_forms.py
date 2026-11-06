"""Validated, metadata-free raster uploads. Images are never served from public storage URLs."""
from io import BytesIO
import warnings
from PIL import Image,ImageOps
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from .forms import LocalizedFieldsMixin
from .models import TeamPhoto,EventExperience,ExperiencePhoto

UPLOAD_NOTICE='Please upload photos of the people you would like to feature, including students, teachers, and team members. Only upload photos you have permission to share. Photos of children require parent or guardian consent.'

def clean_photo(upload):
    if upload.size>settings.MAX_IMAGE_BYTES: raise ValidationError('The photo is too large.')
    if getattr(upload,'content_type','') not in ['image/jpeg','image/png','image/webp']: raise ValidationError('Choose a JPEG, PNG, or WebP image.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            image=Image.open(upload)
            if image.format not in ['JPEG','PNG','WEBP'] or image.width*image.height>24000000: raise ValueError()
            image=ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((2400,2400))
            data=BytesIO();image.save(data,format='JPEG',quality=88)
        if data.tell()>settings.MAX_IMAGE_BYTES: raise ValueError()
        return ContentFile(data.getvalue(),name='photo.jpg')
    except Exception as error: raise ValidationError('Choose a valid image up to 24 megapixels.') from error

class MultipleInput(forms.ClearableFileInput): allow_multiple_selected=True
class MultiplePhotos(forms.FileField):
    widget=MultipleInput(attrs={'accept':'image/jpeg,image/png,image/webp'})
    def clean(self,data,initial=None):
        if not data:return []
        items=data if isinstance(data,(list,tuple)) else [data]
        if len(items)>3: raise ValidationError('Upload up to three photos at a time.')
        if sum(item.size for item in items)>3*1024*1024: raise ValidationError('The combined photo upload must be 3 MB or smaller.')
        return [clean_photo(super(MultiplePhotos,self).clean(item,initial)) for item in items]

class ExperienceForm(LocalizedFieldsMixin,forms.ModelForm):
    photos=MultiplePhotos(required=False,label='Photos')
    photo_description=forms.CharField(max_length=300,required=False,label='Photo description',help_text='Describe the photos for people who cannot see them.')
    permission=forms.BooleanField(required=False,label='I have permission to share these photos, including parent or guardian consent for children shown.')
    class Meta:
        model=EventExperience
        fields=['body']
        labels={'body':'Share your experience'}
        widgets={'body':forms.Textarea(attrs={'rows':4})}
    def clean(self):
        data=super().clean()
        if not data.get('body','').strip() and not data.get('photos') and not (self.instance.pk and self.instance.photos.exists()): raise ValidationError('Add a comment or photo.')
        if data.get('photos'):
            if not data.get('permission'): self.add_error('permission','Confirm permission before sharing photos.')
            if not data.get('photo_description'): self.add_error('photo_description','Add an accessible photo description.')
            if self.instance.pk and self.instance.photos.count()+len(data['photos'])>12: self.add_error('photos','Each contribution can contain up to twelve photos.')
        return data

class TeamPhotoForm(LocalizedFieldsMixin,forms.ModelForm):
    class Meta:
        model=TeamPhoto
        fields=['school','name','role','is_student','is_group','includes_children','image','description','caption','visibility','sharing_permission','guardian_consent']
        help_texts={'name':'Student public display uses the first name only.','guardian_consent':'Required before sharing photos that include children.'}
    def clean_image(self):
        image=self.cleaned_data.get('image')
        return clean_photo(image) if image and hasattr(image,'content_type') else image
    def clean(self):
        data=super().clean()
        if data.get('visibility')!='private':
            if not data.get('sharing_permission'): self.add_error('sharing_permission','Confirm permission before sharing photos.')
            if (data.get('is_student') or data.get('includes_children')) and not data.get('guardian_consent'): self.add_error('guardian_consent','Parent or guardian consent is required for student or group photos.')
        return data

class PhotoCaptionForm(LocalizedFieldsMixin,forms.ModelForm):
    class Meta:
        model=ExperiencePhoto
        fields=['description','caption']

class ReportExperienceForm(LocalizedFieldsMixin,forms.Form):
    reason=forms.CharField(max_length=1000,label='Reason for reporting',widget=forms.Textarea(attrs={'rows':3}))


class InlineTeamPhotoForm(LocalizedFieldsMixin,forms.Form):
    image=forms.FileField(label='Photos',widget=forms.FileInput(attrs={'accept':'image/jpeg,image/png,image/webp'}))
    def clean_image(self):
        return clean_photo(self.cleaned_data['image'])
