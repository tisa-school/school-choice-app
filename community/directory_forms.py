from django import forms
from .models import SchoolProfile
from .forms import LocalizedFieldsMixin
from .discovery import LANGUAGES

AGE_GROUPS=[('','All ages'),('3-5','3–5 years'),('6-8','6–8 years'),('9-12','9–12 years'),('13-17','13–17 years')]
INTERESTS=[('','All interests'),('Arts','Art'),('Sports','Sports'),('Science','Science'),('Music','Music'),('Nature','Nature'),('Theater & Drama','Theatre')]

class DiscoveryFieldsMixin(LocalizedFieldsMixin):
    def __init__(self,*args,**kwargs):
        kwargs.setdefault('label_suffix','')
        super().__init__(*args,**kwargs)

class ActivityDiscoveryForm(DiscoveryFieldsMixin,forms.Form):
    q=forms.CharField(label='Search activities',required=False,max_length=200)
    age_group=forms.ChoiceField(label='Age group',choices=AGE_GROUPS,required=False)
    age=forms.IntegerField(label='Exact age (optional)',required=False,min_value=0,max_value=17)
    date_from=forms.DateField(label='From date',required=False,widget=forms.DateInput(attrs={'type':'date'}))
    date_to=forms.DateField(label='To date',required=False,widget=forms.DateInput(attrs={'type':'date'}))
    category=forms.CharField(label='Category',required=False,max_length=30)
    area=forms.CharField(label='Neighbourhood',required=False,max_length=100)
    price=forms.ChoiceField(label='Price',required=False,choices=[('','Any price'),('free','Free'),('paid','Paid'),('unknown','Price to confirm')])
    max_price=forms.DecimalField(label='Maximum listed price (€)',required=False,min_value=0,max_digits=10,decimal_places=2)
    environment=forms.ChoiceField(label='Setting',required=False,choices=[('','Any setting'),('indoor','Indoor'),('outdoor','Outdoor'),('mixed','Mixed')])
    language=forms.ChoiceField(label='Activity language',choices=[('','Any language')]+LANGUAGES,required=False)
    weekend=forms.BooleanField(label='This weekend',required=False)
    def clean(self):
        data=super().clean()
        if data.get('date_from') and data.get('date_to') and data['date_to']<data['date_from']:self.add_error('date_to','The end date must follow the start date.')
        return data

class SchoolSearchForm(DiscoveryFieldsMixin,forms.Form):
    q=forms.CharField(label='School name or location',max_length=150,required=False)
    age_group=forms.ChoiceField(label='Age group',choices=AGE_GROUPS,required=False)
    stage=forms.ChoiceField(label='Educational stage',choices=[('','Any stage')]+SchoolProfile.STAGES,required=False)
    school_type=forms.ChoiceField(label='School type',choices=[('','Any type')]+SchoolProfile.TYPES,required=False)
    language=forms.ChoiceField(label='Teaching language',choices=[('','Any language')]+LANGUAGES,required=False)
    curriculum=forms.CharField(label='Curriculum',max_length=200,required=False)
    max_fee=forms.DecimalField(label='Maximum starting annual fee (€)',min_value=0,max_digits=10,decimal_places=2,required=False)

    city=forms.CharField(label='Town or city',max_length=100,required=False)
    sort=forms.ChoiceField(label='Sort schools',required=False,choices=[('', 'Name A–Z'),('name_desc','Name Z–A'),('recent','Recently checked'),('fee','Lowest published starting fee')])

class SchoolProfileForm(DiscoveryFieldsMixin,forms.ModelForm):
    stages=forms.MultipleChoiceField(choices=SchoolProfile.STAGES,required=False,widget=forms.CheckboxSelectMultiple)
    class Meta:
        model=SchoolProfile
        exclude=['school','slug','updated_at']
        widgets={'last_checked':forms.DateInput(attrs={'type':'date'})}
        help_texts={'languages':'Comma-separated language codes, for example en,pt.','annual_fee_from':'Annual EUR amount only; include academic year and coverage. Do not estimate.','source_name':'State where these facts came from. Publish only sourced information.','is_published':'Unpublish incomplete or outdated information until it can be checked.'}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if self.instance.pk:self.initial['stages']=self.instance.stages.split(',') if self.instance.stages else []
    def clean_stages(self):return ','.join(self.cleaned_data['stages'])
    def clean_languages(self):
        value=self.cleaned_data['languages'];codes=list(dict.fromkeys(s.strip().lower() for s in value.split(',') if s.strip()))
        if any(s not in dict(LANGUAGES) for s in codes):raise forms.ValidationError('Use the supported language codes shown in the search filters.')
        return ','.join(codes)
