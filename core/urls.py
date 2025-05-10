from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    PostListCreateView, EventListCreateView, RSVPEventView, MarkGroupMessageReadView, vote_poll_option,
    MarketplaceListView, MarketplaceCreateView, RegisterView, SwappOfferCreateView,
    LeaderboardView, FeedbackListView, ReactionCreateView, ThreadView,
    CustomLoginView, UserDetailView, NotificationListView, PostDetailView, GroupListCreateView,
    PublicProfileView, UserProfileView, CommentListCreateView, EventDetailView, LeaveGroupView,
    MessageListCreateView, NotificationUpdateView, ReportListView, ThreadListView, JoinGroupView,
    ReportCreateView, ReportActionView, toggle_save_item, FeedbackCreateView, GroupMessageListCreateView,
     SwappOfferListView, SwappOfferDetailView, SwappOfferAcceptView, SwappOfferDeclineView, SwappOfferCounterView,
     SwappOfferActionView, MySwappOffersView, PublicGroupListView,
)


urlpatterns = [
    # Authentication & Users
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='custom_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('user/profile/', UserProfileView.as_view(), name='user-profile'),
    path('user/public/<int:id>/', PublicProfileView.as_view(), name='user-public'),
    path('polls/vote/<int:option_id>/', vote_poll_option, name='vote_poll'),
    # Posts & Comments
    path('posts/', PostListCreateView.as_view(), name='post-list-create'),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('posts/<int:post_id>/comments/', CommentListCreateView.as_view(), name='comment-list-create'),

    # Events
    path('events/', EventListCreateView.as_view(), name='event-list-create'),
    path('events/<int:pk>/', EventDetailView.as_view(), name='event-detail'),
    path('events/<int:pk>/rsvp/', RSVPEventView.as_view(), name='rsvp-event'),

    # Marketplace
    path('marketplace/', MarketplaceListView.as_view(), name='marketplace'),
    path('marketplace/create/', MarketplaceCreateView.as_view(), name='marketplace-create'),
    path('marketplace/<int:pk>/save/', toggle_save_item, name='toggle-save-item'),

    # Swapp Offers
    path('swapp/offer/', SwappOfferCreateView.as_view(), name='swapp-offer-create'),
    path('swapp/offers/', SwappOfferListView.as_view(), name='swapp-offer-list'),
    path('swapp/offers/<int:pk>/', SwappOfferDetailView.as_view(), name='swapp-offer-detail'),
    path('swapp/offers/<int:pk>/accept/', SwappOfferAcceptView.as_view(), name='swapp-offer-accept'),
    path('swapp/offers/<int:pk>/decline/', SwappOfferDeclineView.as_view(), name='swapp-offer-decline'),
    path('swapp/offers/<int:pk>/counter/', SwappOfferCounterView.as_view(), name='swapp-offer-counter'),

    path('swapp/my-offers/', MySwappOffersView.as_view(), name='my-swapp-offers'),
    path('swapp/offer/<int:pk>/action/', SwappOfferActionView.as_view(), name='swapp-offer-action'),
    # Notifications
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/<int:pk>/', NotificationUpdateView.as_view(), name='notification-update'),

    path('reactions/', ReactionCreateView.as_view(), name='reaction-create'),

    # Messaging
    path('messages/', MessageListCreateView.as_view(), name='message-list-create'),
    path('messages/thread/<int:user_id>/', ThreadView.as_view(), name='thread'),
    path('messages/threads/', ThreadListView.as_view(), name='threads'),
    path('groups-public/', PublicGroupListView.as_view(), name='group-list-create'),
    path('groups/', GroupListCreateView.as_view(), name='group-list-create'),
    path('groups/<int:group_id>/read/', MarkGroupMessageReadView.as_view(), name='mark-group-read'),
    path('groups/<int:group_id>/messages/', GroupMessageListCreateView.as_view(), name='group-messages'),
    path('groups/<int:group_id>/join/', JoinGroupView.as_view(), name='join-group'),
    path('groups/<int:group_id>/leave/', LeaveGroupView.as_view(), name='leave-group'),


    # Reports
    path('report/', ReportCreateView.as_view(), name='report-create'),
    path('report/<int:pk>/', ReportActionView.as_view(), name='report-action'),
    path('reports/', ReportListView.as_view(), name='report-list'),

    # Feedback
    path('feedback/', FeedbackCreateView.as_view(), name='feedback-create'),
    path('feedback/admin/', FeedbackListView.as_view(), name='feedback-admin'),

    # Leaderboard
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
]

# Static/media file serving during development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
