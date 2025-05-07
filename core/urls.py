from django.urls import path
from .views import PostListCreateView, EventListCreateView, RSVPEventView, MarketplaceItemListCreateView, RegisterView, SwappOfferCreateView, SwappOfferUpdateView, LeaderboardView
from .views import CustomLoginView, UserDetailView, NotificationListView, MessageListCreateView, NotificationUpdateView, ReportListView, ReportCreateView, ReportActionView, toggle_save_item, FeedbackCreateView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('posts/', PostListCreateView.as_view(), name='post-list-create'),
    path('events/', EventListCreateView.as_view(), name='event-list-create'),
    path('events/<int:pk>/rsvp/', RSVPEventView.as_view(), name='rsvp-event'),
    path('marketplace/', MarketplaceItemListCreateView.as_view(), name='marketplace'),
    path('swapp/offer/', SwappOfferCreateView.as_view(), name='swapp-offer'),
    path('swapp/offer/<int:pk>/', SwappOfferUpdateView.as_view(), name='swapp-offer-update'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='custom_login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/<int:pk>/', NotificationUpdateView.as_view(), name='notification-update'),
    path('reports/', ReportListView.as_view(), name='report-list'),
    path('marketplace/<int:pk>/save/', toggle_save_item, name='toggle-save-item'),
    path('report/', ReportCreateView.as_view(), name='report-create'),
    path('report/<int:pk>/', ReportActionView.as_view(), name='report-action'),
    path('feedback/', FeedbackCreateView.as_view(), name='feedback-create'),
    path('messages/', MessageListCreateView.as_view(), name='message-list-create'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
]

