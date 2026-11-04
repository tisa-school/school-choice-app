from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from django.utils import timezone

CATEGORIES = [('Sports','Sports'),('Music','Music'),('Arts','Arts'),('School Life','School Life')]
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
    role = models.CharField(max_length=12, choices=[('student','Student'),('staff','Staff')], default='student')
    verified = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
class Event(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
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
    status = models.CharField(max_length=12, choices=[('draft','Draft'),('published','Published')], default='draft')
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    @property
    def remaining(self): return None if self.capacity is None else max(0,self.capacity-self.requests.filter(status='approved').count())
    @property
    def eligible(self): return self.status=='published' and self.ticket_requests_enabled and self.start_at>timezone.now() and (not self.requests_close_at or self.requests_close_at>timezone.now()) and self.remaining != 0
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
