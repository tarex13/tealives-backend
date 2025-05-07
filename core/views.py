from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import Post, Event, Notification, MarketplaceItem, Message
from .serializers import PostSerializer, EventSerializer, RegisterSerializer, NotificationSerializer
from rest_framework.generics import ListAPIView, UpdateAPIView, RetrieveAPIView, CreateAPIView
from .models import MarketplaceItem, SwappOffer, Group
from .serializers import MarketplaceItemSerializer, SwappOfferSerializer
from django.contrib.auth import get_user_model
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer, UserSerializer, GroupSerializer
from .models import Report, Feedback
from .permissions import IsModerator
from .serializers import ReportSerializer, FeedbackSerializer, MessageSerializer
from rest_framework.permissions import BasePermission, IsAuthenticatedOrReadOnly

def award_xp(user, amount):
    user.xp += amount
    user.save()

class LeaderboardView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        city = request.query_params.get('city')
        top_users = User.objects.filter(city=city).order_by('-xp')[:10]
        data = [
            {"username": u.username, "xp": u.xp}
            for u in top_users
        ]
        return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_save_item(request, pk):
    item = MarketplaceItem.objects.get(pk=pk)
    user = request.user

    if item.saved_by.filter(id=user.id).exists():
        item.saved_by.remove(user)
        return Response({'status': 'unsaved'})
    else:
        item.saved_by.add(user)
        return Response({'status': 'saved'})

class IsModerator(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_moderator

class ReportListView(ListAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsModerator]

    def get_queryset(self):
        return Report.objects.filter(is_handled=False).order_by('-created_at')

class ReportCreateView(generics.CreateAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)

class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(sender=user) | Message.objects.filter(recipient=user)

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

class ReportActionView(APIView):
    permission_classes = [IsModerator]

    def patch(self, request, pk):
        report = Report.objects.get(pk=pk)
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

class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    
class PostListCreateView(generics.ListCreateAPIView):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        city = self.request.query_params.get('city')
        return Post.objects.filter(city=city).order_by('-created_at') if city else Post.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, city=self.request.user.city)
        award_xp(self.request.user, 5)

class EventListCreateView(generics.ListCreateAPIView):
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        city = self.request.query_params.get('city')
        return Event.objects.filter(city=city).order_by('datetime') if city else Event.objects.all()

    def perform_create(self, serializer):
        serializer.save(host=self.request.user, city=self.request.user.city)
        award_xp(self.request.user, 10)

class RSVPEventView(generics.UpdateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        event = self.get_object()
        user = request.user

        if user not in event.rsvps.all():
            event.rsvps.add(user)
            award_xp(user, 5)

        return Response({'message': 'RSVP successful'}, status=status.HTTP_200_OK)
    

class PublicGroupListView(generics.ListAPIView):
    serializer_class = GroupSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        city = self.request.query_params.get('city')
        return Group.objects.filter(is_public=True, city=city)

class JoinGroupView(generics.UpdateAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        group = self.get_object()
        user = request.user

        if group.requires_approval:
            # Later: add join requests to queue
            return Response({'message': 'Request sent for approval'}, status=202)
        else:
            group.members.add(user)
            return Response({'message': 'Joined group'})


class MarketplaceItemListCreateView(generics.ListCreateAPIView):
    serializer_class = MarketplaceItemSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return MarketplaceItem.objects.filter(status='available')

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

class SwappOfferUpdateView(generics.UpdateAPIView):
    queryset = SwappOffer.objects.all()
    serializer_class = SwappOfferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        response = super().update(request, *args, **kwargs)

        if request.data.get('status') == 'accepted':
            award_xp(instance.offered_by, 20)

        return response
        

class SwappOfferCreateView(generics.CreateAPIView):
    serializer_class = SwappOfferSerializer
    permission_classes = [permissions.IsAuthenticated]
    

    def perform_create(self, serializer):
        offer = serializer.save(offered_by=self.request.user)
        award_xp(self.request.user, 10)

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    
class MessageCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        recipient_id = request.data.get('recipient')
        content = request.data.get('content')

        if not recipient_id or not content:
            return Response({'error': 'Recipient and content are required'}, status=400)

        if int(recipient_id) == request.user.id:
            return Response({'error': "You can't message yourself."}, status=400)

        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        Message.objects.create(
            sender=request.user,
            recipient=recipient,
            content=content
        )

        return Response({'message': 'Message sent.'}, status=201)
    
class ThreadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            other_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        # Filter messages where current user is either sender or recipient
        messages = Message.objects.filter(
            (Q(sender=request.user) & Q(recipient=other_user)) |
            (Q(sender=other_user) & Q(recipient=request.user))
        ).order_by('sent_at')

        return Response([
            {
                'content': msg.content,
                'is_own': msg.sender == request.user,
                'sent_at': msg.sent_at,
            }
            for msg in messages
        ])
        
class UserDetailView(RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    
class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class NotificationUpdateView(UpdateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.all()

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
class FeedbackCreateView(CreateAPIView):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()