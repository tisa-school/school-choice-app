from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from django.utils import timezone

CATEGORIES = [('Sports','Sports'),('Music','Music'),('Arts','Arts'),('School Life','School Life'),('Science','Science'),('Nature','Nature'),('Coding','Coding'),('Games','Games')]
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
    venue = models.CharField(max_length=160)
    organizer = models.CharField(max_length=160, blank=True)
    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField(null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    price_text = models.CharField(max_length=100, blank=True)
    ticket_requests_enabled = models.BooleanField(default=True)
    requests_close_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=[('draft','Draft'),('submitted','Awaiting staff review'),('published','Published')], default='draft')
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    @property
    def remaining(self): return None if self.capacity is None else max(0,self.capacity-self.requests.filter(status='approved').count()-self.participations.filter(status='confirmed',session__isnull=True).count())
    @property
    def eligible(self): return self.listing_type=='event' and self.status=='published' and self.ticket_requests_enabled and self.start_at>timezone.now() and (not self.requests_close_at or self.requests_close_at>timezone.now()) and self.remaining != 0
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
    venue = models.CharField(max_length=160, blank=True)
    is_cancelled = models.BooleanField(default=False)
    @property
    def remaining(self):
        return None if self.capacity is None else max(0,self.capacity-self.participations.filter(status='confirmed').count())
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
