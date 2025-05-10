from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField



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
    bio = models.TextField(blank=True)
    profile_image = CloudinaryField('image', blank=True, null=True)
    saved_listings = models.ManyToManyField('MarketplaceItem', blank=True, related_name='saved_by_users')


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
    email = models.EmailField(blank=True, null=True)  # Add this line to store optional email
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
    class Meta:
        ordering = ['created_by']

class GroupChat(models.Model):
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(User, related_name='group_chats')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['created_at']

class GroupMessage(models.Model):
    group = models.ForeignKey(GroupChat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(User, related_name='read_group_messages', blank=True)


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
    comment_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
class PollOption(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='poll_options')
    text = models.CharField(max_length=255)
    votes = models.ManyToManyField(User, blank=True, related_name='voted_options')
    
class Event(models.Model):
    host = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    datetime = models.DateTimeField()
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=50)
    is_public = models.BooleanField(default=True)
    rsvps = models.ManyToManyField(User, related_name='rsvped_events', blank=True)
    rsvp_limit = models.PositiveIntegerField(null=True, blank=True)
    show_countdown = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.title} in {self.city} on {self.datetime}"
    
    
# models.py
class Reaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post', 'emoji')
        
class MarketplaceItem(models.Model):
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('used', 'Used'),
        ('fair', 'Fair'),
    ]

    DELIVERY_CHOICES = [
        ('pickup', 'Pickup'),
        ('dropoff', 'Drop-off'),
        ('shipping', 'Shipping'),
        ('meetup', 'Meet in Public'),
    ]

    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100)
    delivery_options = models.CharField(max_length=50, choices=DELIVERY_CHOICES, default='pickup')
    delivery_note = models.TextField(blank=True, null=True)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='used')
    status = models.CharField(max_length=20, default='available')
    city = models.CharField(max_length=50)
    expiry_date = models.DateField(null=True, blank=True)
    views_count = models.PositiveIntegerField(default=0)
    saved_by = models.ManyToManyField('core.User', related_name='saved_items', blank=True)
    
    def __str__(self):
        return self.title


class MarketplaceMedia(models.Model):
    item = models.ForeignKey('MarketplaceItem', related_name='media', on_delete=models.CASCADE)
    file = CloudinaryField('file', folder='marketplace/media/')
    is_video = models.BooleanField(default=False)

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

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    anonymous = models.BooleanField(default=False)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {'Anon' if self.anonymous else self.user.username} on {self.post.title[:20]}"

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