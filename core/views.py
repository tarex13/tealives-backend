from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers
from rest_framework.viewsets import ModelViewSet

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.generics import ListAPIView, UpdateAPIView, RetrieveAPIView, CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly, BasePermission
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils.text import slugify
from django.db.models import Count, F, IntegerField, Value
from django.db.models.functions import Coalesce
from rest_framework.exceptions import ValidationError
from rest_framework import filters
from django.db.models import Case, When, IntegerField, Sum
from .models import (
    Post, Event, Notification, MarketplaceItem,
    Message, Comment, SwappOffer, Group, Reaction, PollOption,
    Report, Feedback, MarketplaceMedia, GroupChat, GroupMessage,
)
from .serializers import (
    PostSerializer, EventSerializer, RegisterSerializer,
    NotificationSerializer, UserProfileSerializer, ReactionSerializer,
    MarketplaceItemSerializer, SwappOfferSerializer,
    CommentSerializer, CustomTokenObtainPairSerializer,
    UserSerializer, GroupSerializer, ReportSerializer, GroupMessageSerializer,
    FeedbackSerializer, MessageSerializer, MiniUserSerializer,
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


from django.db.models import Count, Case, When, Value, IntegerField, Sum  # ensure these are imported

class PostListCreateView(generics.ListCreateAPIView):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'content']
    
    REACTION_WEIGHTS = {
        '👍': 1,
        '❤️': 2,
        '😂': 1,
        '👎': -1,
    }

    def get_queryset(self):
        city = self.request.query_params.get('city', '').strip().lower()
        sort = self.request.query_params.get('sort', 'newest')
        category = self.request.query_params.get('category', '').strip().lower()

        qs = Post.objects.filter(city=city) if city else Post.objects.all()

        if city:
            qs = qs.filter(city__iexact=city)
        if category:
            qs = qs.filter(category__iexact=category)

        if sort == 'hottest':
            when_conditions = [
                When(reactions__emoji=emoji, then=Value(weight))
                for emoji, weight in self.REACTION_WEIGHTS.items()
            ]
            qs = qs.annotate(score=Sum(Case(*when_conditions, output_field=IntegerField()))).order_by('-score', '-created_at')
        elif sort == 'discussed':
            return qs.order_by('-comment_count', '-created_at')
        elif sort == 'highlights':
            qs = qs.annotate(score=Count('comments') + Count('reactions')).order_by('-score', '-created_at')
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

        # ✅ attach user and city automatically
        serializer.save(user=user, city=user_city.lower())
        award_xp(user, 5)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def handle_swapp_action(request, pk):
    offer = get_object_or_404(SwappOffer, pk=pk)
    action = request.data.get('action')
    cash_difference = request.data.get('cash_difference', 0)

    if action == 'accept':
        offer.status = 'accepted'
    elif action == 'decline':
        offer.status = 'declined'
    elif action == 'counter':
        offer.status = 'countered'
        offer.cash_difference = cash_difference
        # You could also handle offered_item changes here if needed
    else:
        return Response({'error': 'Invalid action'}, status=400)

    offer.is_seen = False
    offer.save()
    return Response({'status': offer.status})

# views.py
class ReactionCreateView(generics.CreateAPIView):
    serializer_class = ReactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        post = serializer.validated_data['post']
        emoji = serializer.validated_data['emoji']
        user = self.request.user

        # Optional: toggle behavior
        existing = Reaction.objects.filter(post=post, user=user, emoji=emoji).first()
        if existing:
            existing.delete()
        else:
            serializer.save(user=user)



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
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # update the post's comment count
        if self.post:
            self.post.comment_count = self.post.comments.count()
            self.post.save(update_fields=['comment_count'])

    def delete(self, *args, **kwargs):
        post = self.post
        super().delete(*args, **kwargs)
        if post:
            post.comment_count = post.comments.count()
            post.save(update_fields=['comment_count'])


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
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        city = getattr(user, 'city', None)
        if not city:
            raise ValidationError("User must have a city to create a listing.")

        item = serializer.save(seller=user, city=city)

        for file in self.request.FILES.getlist('images'):
            self.validate_file(file)
            is_video = file.content_type.startswith('video')
            MarketplaceMedia.objects.create(item=item, file=file, is_video=is_video)

        award_xp(user, 10)

    def validate_file(self, file):
        ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov']
        MAX_UPLOAD_SIZE_MB = 20
        ext = file.name.rsplit('.', 1)[-1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(f"Unsupported file extension: .{ext}")
        if file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise ValidationError(f"File too large (max {MAX_UPLOAD_SIZE_MB}MB)")



class SwappOfferListView(generics.ListAPIView):
    serializer_class = SwappOfferSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        view_type = self.request.query_params.get('type', 'received')

        if view_type == 'sent':
            return SwappOffer.objects.filter(offered_by=user).order_by('-date_created')
        return SwappOffer.objects.filter(item__seller=user).order_by('-date_created')


class SwappOfferDetailView(generics.RetrieveAPIView):
    queryset = SwappOffer.objects.all()
    serializer_class = SwappOfferSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return SwappOffer.objects.filter(Q(offered_by=user) | Q(item__seller=user))


class SwappOfferAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        offer = get_object_or_404(SwappOffer, pk=pk)

        if offer.item.seller != request.user:
            return Response({'error': 'You are not the seller of this item.'}, status=403)

        offer.status = 'accepted'
        offer.save()

        # Mark item as swapped/sold
        offer.item.status = 'traded'
        offer.item.save()

        # XP Reward
        award_xp(offer.offered_by, 20)
        award_xp(request.user, 20)

        return Response({'status': 'Offer accepted successfully.'})


class SwappOfferDeclineView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        offer = get_object_or_404(SwappOffer, pk=pk)

        if offer.item.seller != request.user:
            return Response({'error': 'You are not the seller of this item.'}, status=403)

        offer.status = 'declined'
        offer.save()

        return Response({'status': 'Offer declined.'})


class SwappOfferCounterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        offer = get_object_or_404(SwappOffer, pk=pk)

        if offer.item.seller != request.user:
            return Response({'error': 'You are not the seller of this item.'}, status=403)

        counter_cash = request.data.get('cash_difference')
        message = request.data.get('message', '')

        if counter_cash is None:
            return Response({'error': 'You must provide a cash difference for the counter.'}, status=400)

        offer.status = 'countered'
        offer.cash_difference = counter_cash
        offer.message = message
        offer.save()

        return Response({'status': 'Offer countered successfully.'})
    
# List all offers related to the current user
class MySwappOffersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sent = SwappOffer.objects.filter(offered_by=request.user)
        received = SwappOffer.objects.filter(item__seller=request.user)
        return Response({
            'sent': SwappOfferSerializer(sent, many=True).data,
            'received': SwappOfferSerializer(received, many=True).data
        })

# Handle Offer Actions (Accept/Decline/Counter)
class SwappOfferActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        offer = get_object_or_404(SwappOffer, pk=pk)
        action = request.data.get('action')
        if offer.item.seller != request.user:
            return Response({'error': 'Unauthorized.'}, status=403)

        if action == 'accept':
            offer.status = 'accepted'
            offer.save()
            # Notify user
        elif action == 'decline':
            offer.status = 'declined'
            offer.save()
        elif action == 'counter':
            offer.status = 'countered'
            offer.cash_difference = request.data.get('cash_difference', offer.cash_difference)
            offer.message = request.data.get('message', offer.message)
            offer.save()
        else:
            return Response({'error': 'Invalid action.'}, status=400)

        return Response(SwappOfferSerializer(offer).data)

class SwappOfferCreateView(CreateAPIView):
    serializer_class = SwappOfferSerializer
    permission_classes = [IsAuthenticated]
    

    def perform_create(self, serializer):
        Notification.objects.create(
            user=offer.item.seller,
            content=f"{offer.offered_by.username} made a Swapp offer on your item: {offer.item.title}.",
            link=f"/my-swapps"
                )
        serializer.save(offered_by=self.request.user)
        
        
        


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
    
class EventDetailView(RetrieveAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.AllowAny]

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
        return Message.objects.filter(Q(sender=user) | Q(recipient=user)).order_by('-sent_at')

    def perform_create(self, serializer):
        city = self.request.user.city or self.request.data.get("city", "")
        serializer.save(sender=self.request.user)

class ThreadListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        threads = {}

        messages = Message.objects.filter(Q(sender=user) | Q(recipient=user)).order_by('-sent_at')

        for msg in messages:
            other_user = msg.recipient if msg.sender == user else msg.sender

            if other_user.id not in threads:
                total_messages = Message.objects.filter(
                    Q(sender=user, recipient=other_user) | Q(sender=other_user, recipient=user)
                ).count()

                unread_messages = Message.objects.filter(
                    sender=other_user, recipient=user, is_read=False
                ).count()

                threads[other_user.id] = {
                    'type': 'direct',
                    'user': MiniUserSerializer(other_user).data,
                    'last_message': msg.content,
                    'last_message_time': msg.sent_at,
                    'is_unread': unread_messages > 0,
                    'unread_count': unread_messages,
                    'message_count': total_messages,
                }

        # Add group chats
        user_groups = user.group_chats.all()
        for group in user_groups:
            last_msg = group.message_set.order_by('-sent_at').first()
            if last_msg:
                threads[f'group-{group.id}'] = {
                    'type': 'group',
                    'group': {'id': group.id, 'name': group.name},
                    'last_message': last_msg.content,
                    'last_message_time': last_msg.sent_at,
                    'unread_count': 0,  # Add logic for unread if you track this in GroupChat
                    'message_count': group.message_set.count(),
                }

        return Response(list(threads.values()))
    

class MarkGroupMessageReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        group = get_object_or_404(GroupChat, id=group_id)
        messages = group.messages.exclude(read_by=request.user)
        for message in messages:
            message.read_by.add(request.user)
        return Response({'status': 'marked_as_read'})

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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vote_poll_option(request, option_id):
    option = get_object_or_404(PollOption, id=option_id)
    option.votes.add(request.user)
    return Response({'message': 'Vote recorded.'})


class ThreadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        other_user = get_object_or_404(User, id=user_id)

        # Fetch all messages between the two users
        messages = Message.objects.filter(
            Q(sender=request.user, recipient=other_user) |
            Q(sender=other_user, recipient=request.user)
        ).order_by('sent_at')

        # ✅ Mark all unread messages from other_user to current user as read
        unread = messages.filter(sender=other_user, recipient=request.user, is_read=False)
        unread.update(is_read=True)

        # ✅ Format response
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


class ThreadListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        threads = {}

        # Direct Messages
        messages = Message.objects.filter(Q(sender=user) | Q(recipient=user)).order_by('-sent_at')

        for msg in messages:
            other_user = msg.recipient if msg.sender == user else msg.sender
            if other_user.id not in threads:
                threads[other_user.id] = {
                    'type': 'direct',
                    'user': MiniUserSerializer(other_user).data,
                    'last_message': msg.content,
                    'last_message_time': msg.sent_at,
                    'unread_count': Message.objects.filter(sender=other_user, recipient=user, is_read=False).count(),
                    'message_count': Message.objects.filter(
                        Q(sender=user, recipient=other_user) | Q(sender=other_user, recipient=user)
                    ).count(),
                }

        # Group Chats
        for group in user.group_chats.all():
            last_msg = group.messages.order_by('-sent_at').first()
            if last_msg:
                threads[f'group-{group.id}'] = {
                    'type': 'group',
                    'group': GroupSerializer(group).data,
                    'last_message': last_msg.content,
                    'last_message_time': last_msg.sent_at,
                    'unread_count': 0,  # Implement if tracking read states
                    'message_count': group.messages.count(),
                }

        return Response(list(threads.values()))

class GroupListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        groups = GroupChat.objects.all()
        return Response(GroupSerializer(groups, many=True).data)

    def post(self, request):
        name = request.data.get('name')
        if not name:
            return Response({'error': 'Group name is required'}, status=400)
        group = GroupChat.objects.create(name=name)
        group.members.add(request.user)
        return Response(GroupSerializer(group).data, status=201)
    

class PublicGroupListView(ListAPIView):
    serializer_class = GroupSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        city = self.request.query_params.get('city', '').lower()
        return Group.objects.filter(is_public=True, city=city)

class JoinGroupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        group = get_object_or_404(GroupChat, id=group_id)
        group.members.add(request.user)
        return Response({'status': 'joined'}, status=200)

class LeaveGroupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        group = get_object_or_404(GroupChat, id=group_id)
        group.members.remove(request.user)
        return Response({'status': 'left'}, status=200)

class GroupMessageListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, group_id):
        group = get_object_or_404(GroupChat, id=group_id)
        if request.user not in group.members.all():
            return Response({'error': 'Not a member of this group'}, status=403)
        messages = group.messages.order_by('sent_at')
        return Response(GroupMessageSerializer(messages, many=True).data)

    def post(self, request, group_id):
        group = get_object_or_404(GroupChat, id=group_id)
        if request.user not in group.members.all():
            return Response({'error': 'Not a member of this group'}, status=403)
        content = request.data.get('content')
        if not content:
            return Response({'error': 'Message content required'}, status=400)
        message = GroupMessage.objects.create(group=group, sender=request.user, content=content)
        return Response(GroupMessageSerializer(message).data, status=201)


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
    permission_classes = [AllowAny]

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