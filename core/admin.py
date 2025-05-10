from django.contrib import admin
from .models import (
    User, Post, Event, Notification, MarketplaceItem, Reaction, MarketplaceMedia,
    SwappOffer, Feedback, Group, Message, Comment, Report, PollOption, GroupMessage
)
# Register your models here.
class MarketplaceItemAdmin(admin.ModelAdmin):
    pass
class UserAdmin(admin.ModelAdmin):
    pass
class EventAdmin(admin.ModelAdmin):
    pass
class NotificationAdmin(admin.ModelAdmin):
    pass
class ReactionAdmin(admin.ModelAdmin):
    pass
class MarketplaceMediaAdmin(admin.ModelAdmin):
    pass
class SwappOfferAdmin(admin.ModelAdmin):
    pass
class FeedbackAdmin(admin.ModelAdmin):
    pass
class GroupAdmin(admin.ModelAdmin):
    pass
class MessageAdmin(admin.ModelAdmin):
    pass
class CommentAdmin(admin.ModelAdmin):
    pass
class ReportAdmin(admin.ModelAdmin):
    pass
class PollOptionAdmin(admin.ModelAdmin):
    pass
class GroupMessageAdmin(admin.ModelAdmin):
    pass
class PostAdmin(admin.ModelAdmin):
    pass

admin.site.register(GroupMessage, GroupMessageAdmin)
admin.site.register(PollOption, PollOptionAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(MarketplaceMedia, MarketplaceMediaAdmin)
admin.site.register(SwappOffer, SwappOfferAdmin)
admin.site.register(Reaction, ReactionAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(MarketplaceItem, MarketplaceItemAdmin)
admin.site.register(Post, PostAdmin)