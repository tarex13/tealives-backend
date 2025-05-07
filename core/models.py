from django.contrib.auth.models import AbstractUser
from django.db import models



class User(AbstractUser):
    CITY_CHOICES = [
        ('toronto', 'Toronto'),
        ('scarborough', 'Scarborough'),
        ('brampton', 'Brampton'),
        # Add more as needed
    ]

    is_moderator = models.BooleanField(default=False)
    city = models.CharField(max_length=50, choices=CITY_CHOICES, default='toronto')
    is_verified = models.BooleanField(default=False)
    is_business = models.BooleanField(default=False)
    is_moderator = models.BooleanField(default=False)
    xp = models.IntegerField(default=0)

    def __str__(self):
        return self.username
    

class Feedback(models.Model):
    FEEDBACK_TYPES = [
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    type = models.CharField(max_length=20, choices=FEEDBACK_TYPES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.get_type_display()} - {self.content[:40]}'    

class Group(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    city = models.CharField(max_length=100)
    is_public = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    members = models.ManyToManyField(User, related_name='joined_groups', blank=True)

    def __str__(self):
        return self.name



class Post(models.Model):
    POST_TYPES = [
        ('discussion', 'Discussion'),
        ('alert', 'Alert'),
        ('question', 'Question'),
        ('rant', 'Rant'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255)
    content = models.TextField()
    post_type = models.CharField(max_length=20, choices=POST_TYPES)
    city = models.CharField(max_length=50)  # duplicate for filtering speed
    anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
class Event(models.Model):
    host = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    datetime = models.DateTimeField()
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=50)
    is_public = models.BooleanField(default=True)
    rsvps = models.ManyToManyField(User, related_name='rsvped_events', blank=True)

    def __str__(self):
        return f"{self.title} in {self.city} on {self.datetime}"
    
class MarketplaceItem(models.Model):
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('used', 'Used'),
        ('fair', 'Fair'),
    ]

    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100)
    image = models.ImageField(upload_to='marketplace/')
    is_swappable = models.BooleanField(default=False)
    swapp_options = models.JSONField(blank=True, null=True)  # list of items they'd accept
    status = models.CharField(max_length=20, default='available')  # sold, traded, etc.
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='used')
    listing_location = models.CharField(max_length=100)
    expiry_date = models.DateField(null=True, blank=True)
    views_count = models.PositiveIntegerField(default=0)
    saved_by = models.ManyToManyField(
    'core.User',
    related_name='saved_items',
    blank=True
)
    DELIVERY_CHOICES = [
    ('pickup', 'Local Pickup'),
    ('dropoff', 'Drop-off Available'),
    ('shipping', 'Shipping'),
    ('meetup', 'Meet in Public'),
]

    delivery_options = models.CharField(
        max_length=50,
        choices=DELIVERY_CHOICES,
        default='pickup'
    )

    delivery_note = models.TextField(blank=True, null=True)
    
    swapp_wishlist = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

class SwappOffer(models.Model):
    item = models.ForeignKey(MarketplaceItem, on_delete=models.CASCADE, related_name='offers_received')
    offered_by = models.ForeignKey(User, on_delete=models.CASCADE)
    offered_item = models.ForeignKey(MarketplaceItem, on_delete=models.CASCADE, related_name='offers_made', null=True)
    cash_difference = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('countered', 'Countered')
    ], default='pending')
    message = models.TextField(blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    is_seen = models.BooleanField(default=False)

    def __str__(self):
        return f"Offer by {self.offered_by} on {self.item}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    content = models.CharField(max_length=255)
    link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f'Notification for {self.user.username}: {self.content}'

class Report(models.Model):
    CONTENT_TYPES = [
        ('post', 'Post'),
        ('marketplace', 'MarketplaceItem'),
        ('comment', 'Comment'),
    ]

    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    content_id = models.PositiveIntegerField()
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_handled = models.BooleanField(default=False)

    def __str__(self):
        return f"Report: {self.content_type} {self.content_id} by {self.reported_by}"