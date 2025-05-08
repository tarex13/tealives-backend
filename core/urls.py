from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    PostListCreateView, EventListCreateView, RSVPEventView,
    MarketplaceListView, MarketplaceCreateView, RegisterView, SwappOfferCreateView,
    SwappOfferUpdateView, LeaderboardView, FeedbackListView,
    CustomLoginView, UserDetailView, NotificationListView, PostDetailView,
    PublicProfileView, UserProfileView, CommentListCreateView,
    MessageListCreateView, NotificationUpdateView, ReportListView,
    ReportCreateView, ReportActionView, toggle_save_item, FeedbackCreateView
)

urlpatterns = [
    # Authentication & Users
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='custom_login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('user/profile/', UserProfileView.as_view(), name='user-profile'),
    path('user/public/<int:id>/', PublicProfileView.as_view(), name='user-public'),

    # Posts & Comments
    path('posts/', PostListCreateView.as_view(), name='post-list-create'),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('posts/<int:post_id>/comments/', CommentListCreateView.as_view(), name='comment-list-create'),

    # Events
    path('events/', EventListCreateView.as_view(), name='event-list-create'),
    path('events/<int:pk>/rsvp/', RSVPEventView.as_view(), name='rsvp-event'),

    # Marketplace
    path('marketplace/', MarketplaceListView.as_view(), name='marketplace'),
    path('marketplace/create/', MarketplaceCreateView.as_view(), name='marketplace-create'),
    path('marketplace/<int:pk>/save/', toggle_save_item, name='toggle-save-item'),

    # Swapp Offers
    path('swapp/offer/', SwappOfferCreateView.as_view(), name='swapp-offer'),
    path('swapp/offer/<int:pk>/', SwappOfferUpdateView.as_view(), name='swapp-offer-update'),

    # Notifications
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/<int:pk>/', NotificationUpdateView.as_view(), name='notification-update'),

    # Messaging
    path('messages/', MessageListCreateView.as_view(), name='message-list-create'),

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
