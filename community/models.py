from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from django.utils import timezone

CATEGORIES = [('Sports','Sports'),('Music','Music'),('Arts','Arts'),('School Life','School Life'),('Science','Science'),('Nature','Nature'),('Coding','Coding'),('Games','Games'),('Gaming','Gaming'),('Shopping','Shopping'),('Theater & Drama','Theater & Drama')]
class School(models.Model):
    name = models.CharField(max_length=160)
    invite_code_hash = models.CharField(max_length=256)
    time_zone = models.CharField(max_length=64, default='Europe/Lisbon')
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name
    def valid_invite(self, code): return check_password(code, self.invite_code_hash)
class Membership(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    role = models.CharField(max_length=12, choices=[('student','Student'),('staff','Staff'),('parent','Parent'),('organizer','Organizer')], default='student')
    verified = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
class Event(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    listing_type = models.CharField(max_length=12, choices=[('event','Event'),('activity','Activity')], default='event', db_index=True)
    visibility = models.CharField(max_length=12, choices=[('school','School members only'),('public','Public')], default='school', db_index=True)
    min_age = models.PositiveSmallIntegerField(null=True, blank=True)
    max_age = models.PositiveSmallIntegerField(null=True, blank=True)
    languages = models.CharField(max_length=120, blank=True, help_text='Comma-separated language codes: en, pt, fr, es, de, it, nl')
    area = models.CharField(max_length=100, blank=True)
    activity_environment = models.CharField(max_length=12, choices=[('unspecified','Not supplied'),('indoor','Indoor'),('outdoor','Outdoor'),('mixed','Indoor and outdoor')], default='unspecified')
    price_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    supervision = models.TextField(blank=True)
    accessibility = models.TextField(blank=True)
    cancellation_policy = models.TextField(blank=True)
    identity_verified = models.BooleanField(default=False)
    time_zone = models.CharField(max_length=64, default='Europe/Lisbon')
    published_by = models.ForeignKey(User, null=True, blank=True, related_name='published_listings', on_delete=models.SET_NULL)
    title = models.CharField(max_length=180)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    description = models.TextField()
    image = models.ImageField(upload_to='events/', blank=True)
    image_alt = models.CharField(max_length=300, blank=True)
    image_source = models.CharField(max_length=12, blank=True, default='unreviewed', choices=[('unreviewed','Awaiting review'),('event','Photo taken at this event'),('stock','Illustrative stock image'),('generated','AI-generated illustration')])
    image_review_signature = models.CharField(max_length=64, blank=True, editable=False)

    venue = models.CharField(max_length=160)
    organizer = models.CharField(max_length=160, blank=True)
    booking_url = models.URLField(blank=True)
    address = models.CharField(max_length=240, blank=True)
    contact_name = models.CharField(max_length=100, blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    contact_website = models.URLField(max_length=500, blank=True)
    contact_public = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    cancellation_note = models.CharField(max_length=500, blank=True)
    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField(null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    child_capacity = models.PositiveIntegerField(null=True, blank=True)
    price_text = models.CharField(max_length=100, blank=True)
    ticket_requests_enabled = models.BooleanField(default=True)
    requests_close_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=[('draft','Draft'),('submitted','Awaiting staff review'),('published','Published')], default='draft')
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def image_signature(self):
        import hashlib, json
        values=[self.title,self.description,self.category,self.min_age,self.max_age,self.venue,self.area,self.address,self.activity_environment,self.image.name,self.image_alt,self.image_source]
        return hashlib.sha256(json.dumps(values,ensure_ascii=False).encode()).hexdigest()

    @property
    def image_is_reviewed(self):
        return bool(self.image and self.image_alt.strip() and self.image_source in {'event','stock','generated'} and self.image_review_signature==self.image_signature())

    def save(self,*args,**kwargs):
        if self.image and not self.image._committed:
            self.image_review_signature=''
            if kwargs.get('update_fields') is not None:
                kwargs['update_fields']=set(kwargs['update_fields'])|{'image_review_signature'}
        super().save(*args,**kwargs)
        if getattr(self,'_review_event_image',False):
            self._review_event_image=False
            if self.image and self.image_alt.strip() and self.image_source in {'event','stock','generated'}:
                self.image_review_signature=self.image_signature()
                type(self).objects.using(self._state.db).filter(pk=self.pk).update(image_review_signature=self.image_review_signature)

    @property
    def attendance(self):
        from .attendance import attendance
        return attendance(self)
    @property
    def remaining(self): return self.attendance['remaining_total']
    @property
    def remaining_children(self): return self.attendance['remaining_children']
    @property
    def eligible(self): return not self.is_cancelled and self.listing_type=='event' and self.status=='published' and self.ticket_requests_enabled and self.start_at>timezone.now() and (not self.requests_close_at or self.requests_close_at>timezone.now()) and self.remaining != 0
    @property
    def map_url(self):
        from urllib.parse import urlencode
        return 'https://www.openstreetmap.org/search?'+urlencode({'query':self.address}) if self.address else ''
    @property
    def phone_link(self):
        return 'tel:'+''.join(char for char in self.contact_phone if char.isdigit() or char=='+')
    def __str__(self): return self.title
class TicketRequest(models.Model):
    STATUSES = [(s,s.replace('_',' ').title()) for s in ['requested','under_review','approved','declined','cancelled']]
    event = models.ForeignKey(Event, related_name='requests', on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUSES, default='requested')
    reviewed_by = models.ForeignKey(User, null=True, blank=True, related_name='reviews', on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['event','student'],condition=Q(status__in=['requested','under_review','approved']),name='unique_active_request')]
        indexes = [models.Index(fields=['event','status'])]
class TicketHistory(models.Model):
    ticket = models.ForeignKey(TicketRequest, related_name='history',on_delete=models.CASCADE)
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, null=True,on_delete=models.SET_NULL)
    changed_at = models.DateTimeField(auto_now_add=True)
class SavedEvent(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    event = models.ForeignKey(Event,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user','event'],name='unique_save')]
class Collection(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    cover_style = models.CharField(max_length=12, choices=[('crystal','Crystal'),('midnight','Midnight'),('lavender','Lavender')], default='crystal')
    events = models.ManyToManyField(Event, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
class Announcement(models.Model):
    school = models.ForeignKey(School,on_delete=models.CASCADE)
    author = models.ForeignKey(User,on_delete=models.PROTECT)
    title = models.CharField(max_length=180)
    body = models.TextField()
    image = models.ImageField(upload_to='announcements/',blank=True)
    status = models.CharField(max_length=12, choices=[('draft','Draft'),('published','Published'),('scheduled','Scheduled')],default='draft')
    is_pinned = models.BooleanField(default=False)
    scheduled_for = models.DateTimeField(null=True,blank=True)
    published_at = models.DateTimeField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
class Notification(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    school = models.ForeignKey(School,on_delete=models.CASCADE)
    kind = models.CharField(max_length=30)
    title = models.CharField(max_length=180)
    message = models.TextField()
    link = models.CharField(max_length=200,blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
# Notification properties translate system strings in the reader's current language.
class RateAttempt(models.Model):
    key = models.CharField(max_length=100,db_index=True)
    created_at = models.DateTimeField(auto_now_add=True,db_index=True)

class PrivateUpload(models.Model):
    """Small private raster files persist in the managed DB on serverless deployments."""
    name = models.CharField(max_length=255, unique=True)
    data = models.BinaryField()
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class ParentAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    consent_at = models.DateTimeField(auto_now_add=True)

class ChildProfile(models.Model):
    parent = models.ForeignKey(ParentAccount, related_name='children', on_delete=models.CASCADE)
    nickname = models.CharField(max_length=60)
    age_band = models.CharField(max_length=8, choices=[('3-5','3–5'),('6-8','6–8'),('9-11','9–11'),('12-14','12–14'),('15-17','15–17')])
    interests = models.CharField(max_length=200, blank=True)
    languages = models.CharField(max_length=120, blank=True)
    def __str__(self): return self.nickname

class ActivitySession(models.Model):
    activity = models.ForeignKey(Event, related_name='sessions', on_delete=models.CASCADE)
    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField()
    capacity = models.PositiveIntegerField(null=True, blank=True)
    child_capacity = models.PositiveIntegerField(null=True, blank=True)
    venue = models.CharField(max_length=160, blank=True)
    is_cancelled = models.BooleanField(default=False)
    @property
    def attendance(self):
        from .attendance import attendance
        return attendance(self)
    @property
    def remaining(self): return self.attendance['remaining_total']
    @property
    def remaining_children(self): return self.attendance['remaining_children']
    def __str__(self): return str(self.start_at)

class Participation(models.Model):
    STATUSES = [('interested','Interested'),('parent_pending','Awaiting parent approval'),('organizer_pending','Awaiting organizer confirmation'),('confirmed','Confirmed'),('declined','Declined'),('cancelled','Cancelled')]
    child = models.ForeignKey(ChildProfile, related_name='participations', on_delete=models.CASCADE)
    event = models.ForeignKey(Event, related_name='participations', on_delete=models.CASCADE)
    session = models.ForeignKey(ActivitySession, null=True, blank=True, related_name='participations', on_delete=models.CASCADE)
    status = models.CharField(max_length=24, choices=STATUSES, default='interested')
    parent_reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['child','event'], condition=Q(session__isnull=True,status__in=['interested','parent_pending','organizer_pending','confirmed']), name='unique_active_family_event'),
            models.UniqueConstraint(fields=['child','session'], condition=Q(session__isnull=False,status__in=['interested','parent_pending','organizer_pending','confirmed']), name='unique_active_family_session'),
        ]

class ParticipationHistory(models.Model):
    participation = models.ForeignKey(Participation, related_name='history', on_delete=models.CASCADE)
    previous_status = models.CharField(max_length=24, blank=True)
    new_status = models.CharField(max_length=24)
    changed_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    changed_at = models.DateTimeField(auto_now_add=True)

class FamilyPlan(models.Model):
    parent = models.ForeignKey(ParentAccount, related_name='plans', on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    session = models.ForeignKey(ActivitySession, null=True, blank=True, on_delete=models.CASCADE)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['parent','event'],condition=Q(session__isnull=True),name='unique_family_plan_event'),models.UniqueConstraint(fields=['parent','session'],condition=Q(session__isnull=False),name='unique_family_plan_session')]

class SaveReceipt(models.Model):
    """The user's most recent confirmed application write; never a client-side guess."""
    user = models.OneToOneField(User, related_name='save_receipt', on_delete=models.CASCADE)
    action = models.CharField(max_length=120)
    saved_at = models.DateTimeField(auto_now=True)


class OrganizerApplication(models.Model):
    user = models.OneToOneField(User, related_name='organizer_application', on_delete=models.CASCADE)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    organization = models.CharField(max_length=160)
    contact_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=40)
    website = models.URLField(max_length=500, blank=True)
    description = models.TextField()
    status = models.CharField(max_length=12, choices=[('pending','Pending review'),('approved','Approved'),('declined','Declined')], default='pending')
    reviewed_by = models.ForeignKey(User, null=True, blank=True, related_name='reviewed_organizers', on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Feedback(models.Model):
    kind = models.CharField(max_length=12, choices=[('feedback','General feedback'),('suggestion','Suggest an activity'),('report','Report a listing')])
    message = models.TextField(max_length=2000)
    listing = models.ForeignKey(Event, null=True, blank=True, on_delete=models.SET_NULL)
    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.SET_NULL)
    submitted_by = models.ForeignKey(User, null=True, blank=True, related_name='submitted_feedback', on_delete=models.SET_NULL)
    status = models.CharField(max_length=12, choices=[('new','New'),('reviewed','Reviewed'),('resolved','Resolved')], default='new')
    reviewed_by = models.ForeignKey(User, null=True, blank=True, related_name='reviewed_feedback', on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True,db_index=True)


class InterfacePreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    language = models.CharField(max_length=12, default='en')

class FamilyBooking(models.Model):
    parent = models.ForeignKey(ParentAccount, related_name='bookings', on_delete=models.CASCADE)
    event = models.ForeignKey(Event, related_name='family_bookings', on_delete=models.CASCADE)
    session = models.ForeignKey(ActivitySession, related_name='family_bookings', null=True, blank=True, on_delete=models.CASCADE)
    adults = models.PositiveSmallIntegerField(default=0)
    children = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=12, choices=[('pending','Awaiting organizer confirmation'),('confirmed','Confirmed'),('declined','Declined'),('cancelled','Cancelled')], default='pending')
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(adults__gt=0)|Q(children__gt=0), name='booking_has_attendees'),
            models.UniqueConstraint(fields=['parent','event'], condition=Q(session__isnull=True,status__in=['pending','confirmed']), name='unique_active_group_event'),
            models.UniqueConstraint(fields=['parent','session'], condition=Q(session__isnull=False,status__in=['pending','confirmed']), name='unique_active_group_session'),
        ]
    @property
    def total(self): return self.adults+self.children

class EventExperience(models.Model):
    event = models.ForeignKey(Event, related_name='experiences', on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField(max_length=2000, blank=True)
    status = models.CharField(max_length=12, choices=[('pending','Awaiting moderation'),('published','Published'),('hidden','Hidden')], default='pending')
    reviewed_by = models.ForeignKey(User, null=True, blank=True, related_name='moderated_experiences', on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ExperiencePhoto(models.Model):
    experience = models.ForeignKey(EventExperience, related_name='photos', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='experiences/')
    description = models.CharField(max_length=300)
    caption = models.CharField(max_length=300, blank=True)
    hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class ExperienceReport(models.Model):
    experience = models.ForeignKey(EventExperience, related_name='reports', on_delete=models.CASCADE)
    photo = models.ForeignKey(ExperiencePhoto, null=True, blank=True, on_delete=models.CASCADE)
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField(max_length=1000)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['experience','reported_by'],condition=Q(resolved=False),name='one_open_experience_report')]

class TeamPhoto(models.Model):
    school = models.ForeignKey(School, related_name='team_photos', on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    name = models.CharField(max_length=160, blank=True)
    role = models.CharField(max_length=160, blank=True)
    is_student = models.BooleanField(default=False)
    is_group = models.BooleanField(default=False)
    image = models.ImageField(upload_to='team/')
    caption = models.CharField(max_length=300, blank=True)
    description = models.CharField(max_length=300)
    visibility = models.CharField(max_length=12, choices=[('private','Administrators only'),('school','School members only'),('public','Public')], default='private')
    sharing_permission = models.BooleanField(default=False)
    guardian_consent = models.BooleanField(default=False)
    # Group photographs may include children even when no individual student is named.
    includes_children = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    @property
    def display_name(self): return self.name.split()[0] if self.is_student and self.name else self.name

class SchoolProfile(models.Model):
    """Public directory data, separate from private membership/invite records."""
    TYPES=[('public','Public'),('private','Private'),('international','International')]
    STAGES=[('early','Early years'),('primary','Primary'),('lower_secondary','Lower secondary'),('upper_secondary','Upper secondary')]
    school=models.OneToOneField(School,on_delete=models.SET_NULL,null=True,blank=True,related_name='directory_profile')
    slug=models.SlugField(max_length=190,unique=True)
    name=models.CharField(max_length=180)
    city=models.CharField(max_length=100,default='Lisbon',db_index=True)
    neighbourhood=models.CharField(max_length=120,blank=True)
    summary=models.TextField(blank=True)
    school_type=models.CharField(max_length=20,choices=TYPES,blank=True,db_index=True)
    min_age=models.PositiveSmallIntegerField(null=True,blank=True)
    max_age=models.PositiveSmallIntegerField(null=True,blank=True)
    stages=models.CharField(max_length=120,blank=True)
    languages=models.CharField(max_length=120,blank=True)
    curriculum=models.CharField(max_length=200,blank=True)
    teaching_approach=models.TextField(blank=True)
    address=models.CharField(max_length=300,blank=True)
    website=models.URLField(blank=True)
    hours=models.CharField(max_length=200,blank=True)
    facilities=models.TextField(blank=True)
    extracurriculars=models.TextField(blank=True)
    annual_fee_from=models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    annual_fee_to=models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    fee_year=models.CharField(max_length=30,blank=True)
    fee_includes=models.TextField(blank=True)
    admissions=models.TextField(blank=True)
    visit_url=models.URLField(blank=True)
    source_name=models.CharField(max_length=250,blank=True)
    source_url=models.URLField(blank=True)
    last_checked=models.DateField(null=True,blank=True)
    is_published=models.BooleanField(default=False,db_index=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=['name']
    def __str__(self):return self.name
    def clean(self):
        from django.core.exceptions import ValidationError
        from urllib.parse import urlsplit
        errors={}
        if (self.min_age is None)!=(self.max_age is None) or (self.min_age is not None and not 0<=self.min_age<=self.max_age<=21):errors['max_age']='Provide a complete, valid school age range.'
        if self.annual_fee_from is not None and self.annual_fee_from<0:errors['annual_fee_from']='Fees cannot be negative.'
        if self.annual_fee_to is not None and (self.annual_fee_to<0 or self.annual_fee_from is None or self.annual_fee_to<self.annual_fee_from):errors['annual_fee_to']='Provide a consistent annual fee range.'
        if self.annual_fee_from is not None and (not self.fee_year or not self.fee_includes):errors['fee_year']='State the academic year and what the quoted fee covers.'
        for field in ['website','source_url','visit_url']:
            value=getattr(self,field)
            if value:
                try:
                    parsed=urlsplit(value)
                    if parsed.scheme not in ['http','https'] or not parsed.netloc or parsed.username or parsed.password:raise ValueError()
                except ValueError:errors[field]='Use an HTTP or HTTPS website without embedded credentials.'
        if self.is_published and (not self.source_name or not self.last_checked):errors['source_name']='Published profiles need a source and a last-checked date.'
        if self.last_checked and self.last_checked>timezone.localdate():errors['last_checked']='The last-checked date cannot be in the future.'
        if errors:raise ValidationError(errors)
    @property
    def stage_labels(self):return ', '.join(dict(self.STAGES).get(s,s) for s in self.stages.split(',') if s)
    @property
    def language_labels(self):
        from .discovery import LANGUAGES
        return ', '.join(dict(LANGUAGES).get(s,s) for s in self.languages.split(',') if s)
    @property
    def age_label(self):return f'{self.min_age}–{self.max_age}' if self.min_age is not None else ''

class ShortlistedSchool(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='shortlisted_schools')
    profile=models.ForeignKey(SchoolProfile,on_delete=models.CASCADE,related_name='shortlisted_by')
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['user','profile'],name='one_school_shortlist_per_user')]
