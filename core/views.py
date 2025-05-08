from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.generics import ListAPIView, UpdateAPIView, RetrieveAPIView, CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly, BasePermission
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils.text import slugify
from django.db.models import Count, F, IntegerField, Value
from django.db.models.functions import Coalesce
from rest_framework.exceptions import ValidationError
from rest_framework import filters

from .models import (
    Post, Event, Notification, MarketplaceItem,
    Message, Comment, SwappOffer, Group,
    Report, Feedback
)
from .serializers import (
    PostSerializer, EventSerializer, RegisterSerializer,
    NotificationSerializer, UserProfileSerializer,
    MarketplaceItemSerializer, SwappOfferSerializer,
    CommentSerializer, CustomTokenObtainPairSerializer,
    UserSerializer, GroupSerializer, ReportSerializer,
    FeedbackSerializer, MessageSerializer
)

from django.contrib.auth import get_user_model
User = get_user_model()

# ----------------------------------
# 🔐 PERMISSIONS
# ----------------------------------

class IsModerator(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_moderator

class IsAdminOrModerator(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_staff or getattr(request.user, 'is_moderator', False)
        )

class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.method in ['GET', 'HEAD'] or obj.user == request.user

# ----------------------------------
# ⚙️ UTILITY
# ----------------------------------

def award_xp(user, amount):
    user.xp += amount
    user.save()

# ----------------------------------
# 👤 USER & AUTH
# ----------------------------------

class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserDetailView(RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class PublicProfileView(RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

# ----------------------------------
# 🏙️ POSTS & COMMENTS
# ----------------------------------


class PostListCreateView(generics.ListCreateAPIView):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'content']  # ✅ Enable ?search=

    def get_queryset(self):
        city = self.request.query_params.get('city', '').strip().lower()
        sort = self.request.query_params.get('sort', 'newest')
        category = self.request.query_params.get('category', '').strip().lower()

        qs = Post.objects.all()

        if city:
            qs = qs.filter(city__iexact=city)
        if category:
            qs = qs.filter(category__iexact=category)

        if sort == 'hottest':
            qs = qs.annotate(score=Coalesce(F('reactions__count'), Value(0))).order_by('-score', '-created_at')
        elif sort == 'discussed':
            qs = qs.annotate(num_comments=Count('comments')).order_by('-num_comments', '-created_at')
        elif sort == 'highlights':
            # Temporarily skip JSON field to avoid crash
            qs = qs.annotate(score=Count('comments')).order_by('-score', '-created_at')
        elif sort == 'random':
            qs = qs.order_by('?')
        else:
            qs = qs.order_by('-created_at')


        return qs

    def perform_create(self, serializer):
        user = self.request.user
        user_city = getattr(user, 'city', None)

        if not user_city:
            raise ValidationError("User must have a city to create a post.")

        serializer.save(user=user, city=user_city.lower())
        award_xp(user, 5)



class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

class CommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        post_id = self.kwargs['post_id']
        return Comment.objects.filter(post_id=post_id, parent=None).order_by('-created_at')

    def perform_create(self, serializer):
        post = get_object_or_404(Post, pk=self.kwargs['post_id'])

        parent_id = self.request.data.get("parent")
        parent_comment = None

        if parent_id:
            try:
                parent_comment = Comment.objects.get(id=parent_id)
                # Optional safety check: Ensure parent belongs to same post
                if parent_comment.post_id != post.id:
                    raise serializers.ValidationError("Parent comment does not belong to this post.")
            except Comment.DoesNotExist:
                raise serializers.ValidationError("Invalid parent comment.")
            
        print("Saving comment:", {
            "user": self.request.user,
            "post": post.id,
            "parent": parent_comment.id if parent_comment else None
        })


        serializer.save(
            user=self.request.user,
            post=post,
            anonymous=self.request.data.get("anonymous", False),
            parent=parent_comment
        )


# ----------------------------------
# 🛍️ MARKETPLACE & SWAPP
# ----------------------------------

class MarketplaceListView(generics.ListAPIView):
    queryset = MarketplaceItem.objects.filter(status='available')
    serializer_class = MarketplaceItemSerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        qs = MarketplaceItem.objects.filter(status='available')
        city = self.request.query_params.get('city')

        if city:
            return qs.filter(city__iexact=slugify(city))
        return qs

class MarketplaceCreateView(generics.CreateAPIView):
    serializer_class = MarketplaceItemSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        city = getattr(self.request.user, 'city', None) or self.request.data.get("city", "")
        serializer.save(user=self.request.user, city=slugify(city))

class SwappOfferCreateView(CreateAPIView):
    serializer_class = SwappOfferSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        city = self.request.user.city or self.request.data.get("city", "")
        serializer.save(offered_by=self.request.user, city=city.lower())
        award_xp(self.request.user, 10)

class SwappOfferUpdateView(UpdateAPIView):
    queryset = SwappOffer.objects.all()
    serializer_class = SwappOfferSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        response = super().update(request, *args, **kwargs)
        if request.data.get('status') == 'accepted':
            award_xp(instance.offered_by, 20)
        return response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_save_item(request, pk):
    item = get_object_or_404(MarketplaceItem, pk=pk)
    user = request.user

    if item.saved_by.filter(id=user.id).exists():
        item.saved_by.remove(user)
        return Response({'status': 'unsaved'})
    else:
        item.saved_by.add(user)
        return Response({'status': 'saved'})

# ----------------------------------
# 📆 EVENTS & RSVP
# ----------------------------------

class EventListCreateView(generics.ListCreateAPIView):
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        city = self.request.query_params.get('city')
        if isinstance(city, str) and city.strip():
            return Event.objects.filter(city__iexact=city.strip()).order_by('datetime')
        return Event.objects.all().order_by('datetime')


    def perform_create(self, serializer):
        city = self.request.user.city or self.request.data.get("city", "")
        serializer.save(host=self.request.user, city=city.lower())
        award_xp(self.request.user, 10)
        
    def get_serializer_context(self):
        return {'request': self.request}

class RSVPEventView(UpdateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        event = self.get_object()
        user = request.user
        
        if event.datetime < now():
            return Response({'error': 'Cannot RSVP to past events'}, status=400)

        if user in event.rsvps.all():
            event.rsvps.remove(user)
            send_mail(
                subject='You CANCELLED an event RSVP!',
                message=f"Hi {user.username}, you've cancelled your RSVP’d to: {event.title} on {event.datetime.strftime('%Y-%m-%d %H:%M')}.",
                from_email=None,
                recipient_list=[user.email],
)
            return Response({'message': 'RSVP removed'}, status=200)
        else:
            if event.rsvp_limit and event.rsvps.count() >= event.rsvp_limit:
                return Response({'error': 'Event is full'}, status=400)

            event.rsvps.add(user)
            award_xp(user, 5)
            send_mail(
                subject='🎉 You RSVP’d to an event!',
                message=f"Hi {user.username}, you've RSVP’d to: {event.title} on {event.datetime.strftime('%Y-%m-%d %H:%M')}.",
                from_email=None,
                recipient_list=[user.email],
)
            return Response({'message': 'RSVP successful'}, status=200)

# ----------------------------------
# 💬 MESSAGING
# ----------------------------------

class MessageListCreateView(ListAPIView, CreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(Q(sender=user) | Q(recipient=user))

    def perform_create(self, serializer):
        city = self.request.user.city or self.request.data.get("city", "")
        serializer.save(sender=self.request.user, city=city.lower())

class MessageCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        recipient_id = request.data.get('recipient')
        content = request.data.get('content')
        if not recipient_id or not content:
            return Response({'error': 'Recipient and content are required'}, status=400)
        if int(recipient_id) == request.user.id:
            return Response({'error': "You can't message yourself."}, status=400)
        recipient = get_object_or_404(User, id=recipient_id)
        Message.objects.create(sender=request.user, recipient=recipient, content=content)
        return Response({'message': 'Message sent.'}, status=201)

class ThreadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        other_user = get_object_or_404(User, id=user_id)
        messages = Message.objects.filter(
            Q(sender=request.user, recipient=other_user) |
            Q(sender=other_user, recipient=request.user)
        ).order_by('sent_at')

        return Response([
            {
                'content': msg.content,
                'is_own': msg.sender == request.user,
                'sent_at': msg.sent_at,
            } for msg in messages
        ])

# ----------------------------------
# 🧠 MODERATION & ADMIN TOOLS
# ----------------------------------

class ReportListView(ListAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsModerator]

    def get_queryset(self):
        return Report.objects.filter(is_handled=False).order_by('-created_at')

class ReportCreateView(CreateAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user_city = self.request.user.city or self.request.data.get("city", "")
        serializer.save(reported_by=self.request.user, city=user_city.lower())

class ReportActionView(APIView):
    permission_classes = [IsModerator]

    def patch(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        action = request.data.get('action')

        if action == 'delete':
            if report.content_type == 'post':
                Post.objects.filter(id=report.content_id).delete()
            elif report.content_type == 'marketplace':
                MarketplaceItem.objects.filter(id=report.content_id).delete()
        elif action == 'suspend':
            report.reported_by.is_active = False
            report.reported_by.save()

        report.is_handled = True
        report.save()
        return Response({'status': 'handled'})

# ----------------------------------
# 🌐 GROUPS, NOTIFICATIONS, MISC
# ----------------------------------

class PublicGroupListView(ListAPIView):
    serializer_class = GroupSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        city = self.request.query_params.get('city', '').lower()
        return Group.objects.filter(is_public=True, city=city)

class JoinGroupView(UpdateAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        group = self.get_object()
        user = request.user
        if group.requires_approval:
            return Response({'message': 'Request sent for approval'}, status=202)
        else:
            group.members.add(user)
            return Response({'message': 'Joined group'})

class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class NotificationUpdateView(UpdateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

class FeedbackCreateView(CreateAPIView):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            city = self.request.user.city or self.request.data.get("city", "")
            serializer.save(user=self.request.user, city=city.lower())
        else:
            serializer.save()

class FeedbackListView(ListAPIView):
    serializer_class = FeedbackSerializer
    permission_classes = [IsAdminOrModerator]

    def get_queryset(self):
        return Feedback.objects.all().order_by('-created_at')

class LeaderboardView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        city = request.query_params.get('city')
        if not city:
            return Response({'error': 'City is required.'}, status=400)

        city = city.lower()
        top_users = User.objects.filter(city=city).order_by('-xp')[:10]
        data = [{"username": u.username, "xp": u.xp} for u in top_users]
        return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh = RefreshToken(request.data["refresh"])
        refresh.blacklist()
        return Response(status=status.HTTP_205_RESET_CONTENT)
    except Exception as e:
        return Response(status=status.HTTP_400_BAD_REQUEST)