from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from django.db.models import Count
from .models import (
    User, Post, Event, Notification, MarketplaceItem, Reaction, MarketplaceMedia,
    SwappOffer, Feedback, Group, Message, Comment, Report, PollOption, GroupMessage
)
from cloudinary.utils import cloudinary_url
# -----------------------------
# Auth & User
# -----------------------------

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'city': self.user.city,
            'is_verified': self.user.is_verified,
            'is_business': self.user.is_business,
        }
        return data

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id','username', 'email', 'bio', 'city', 'profile_image']
        read_only_fields = ['username', 'email']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'city', 'is_business']


# -----------------------------
# Posts, Events, Comments
# -----------------------------



class EventSerializer(serializers.ModelSerializer):
    has_rsvped = serializers.SerializerMethodField()
    rsvp_count = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'datetime', 'location', 'has_rsvped', 'rsvp_count']

    def get_has_rsvped(self, obj):
        request = self.context.get('request')
        return request.user in obj.rsvps.all() if request else False

    def get_rsvp_count(self, obj):
        return obj.rsvps.count()
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')

        if not request or not hasattr(request, 'user'):
            return data

        if request.user != instance.host:
            data.pop('rsvps', None)

        return data



class RecursiveCommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'content', 'anonymous', 'user', 'created_at', 'parent', 'replies']

    def get_replies(self, obj):
        return RecursiveCommentSerializer(obj.replies.all().order_by('created_at'), many=True).data

    def get_user(self, obj):
        return "Anonymous" if obj.anonymous else obj.user.username


class CommentSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    post = serializers.PrimaryKeyRelatedField(read_only=True)
    parent = serializers.PrimaryKeyRelatedField(queryset=Comment.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Comment
        fields = ['id', 'post', 'user', 'content', 'anonymous', 'parent', 'created_at', 'replies']

    def get_replies(self, obj):
        return CommentSerializer(obj.replies.all().order_by('created_at'), many=True).data

    def get_user(self, obj):
        return "Anonymous" if obj.anonymous else obj.user.username

# -----------------------------
# Marketplace & Swapps
# -----------------------------

class MarketplaceMediaSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = MarketplaceMedia
        fields = ['id', 'file', 'is_video']

    def get_file(self, obj):
        if obj.file:
            url, _ = cloudinary_url(obj.file.public_id, width=400, height=400, crop="fill", quality="auto")
            return url
        return None
        
        
class ThreadSummarySerializer(serializers.Serializer):
    user = UserProfileSerializer()  # or a lightweight serializer
    last_message = serializers.CharField()
    last_message_time = serializers.DateTimeField()
    is_unread = serializers.BooleanField()

class MiniUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'profile_image']

class MarketplaceItemSerializer(serializers.ModelSerializer):
    is_saved = serializers.SerializerMethodField()
    saved_by_user = serializers.SerializerMethodField()
    images = MarketplaceMediaSerializer(source='media', many=True, read_only=True)

    class Meta:
        model = MarketplaceItem
        fields = [
            'id', 'title', 'description', 'price', 'category',
            'delivery_options', 'delivery_note', 'is_saved', 
            'saved_by_user', 'status', 'seller', 'city', 'images'
        ]
        read_only_fields = ['seller', 'city', 'is_saved', 'saved_by_user']

    def get_is_saved(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and obj.saved_by.filter(id=user.id).exists()

    def get_saved_by_user(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and obj.saved_by.filter(id=user.id).exists()





class SwappOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = SwappOffer
        fields = '__all__'
        read_only_fields = ['offered_by', 'status', 'date_created', 'is_seen']

# -----------------------------
# Messaging, Groups, Feedback
# -----------------------------

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['sender', 'city']

class GroupSerializer(serializers.ModelSerializer):
    is_member = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = '__all__'

    def get_is_member(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and obj.members.filter(id=user.id).order_by('name').exists()
    
class GroupMessageSerializer(serializers.ModelSerializer):
    sender = MiniUserSerializer(read_only=True)
    read_by = MiniUserSerializer(many=True, read_only=True)  # ✅ Add this field

    class Meta:
        model = GroupMessage
        fields = ['id', 'group', 'sender', 'content', 'sent_at', 'read_by']

class FeedbackSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True)

    class Meta:
        model = Feedback
        fields = ['type', 'content', 'email']

    def create(self, validated_data):
        email = validated_data.pop('email', None)
        feedback = Feedback.objects.create(**validated_data)
        if email:
            # Store email somewhere or trigger an email notification if needed
            pass
        return feedback

# -----------------------------
# Notifications & Reports
# -----------------------------

ALLOWED_REACTIONS = ['👍', '❤️', '😂']

class PollOptionSerializer(serializers.ModelSerializer):
    votes_count = serializers.SerializerMethodField()

    class Meta:
        model = PollOption
        fields = ['id', 'text', 'votes_count']

    def get_votes_count(self, obj):
        return obj.votes.count()
    

class PostSerializer(serializers.ModelSerializer):
    poll_options = PollOptionSerializer(many=True, read_only=True)
    reaction_summary = serializers.SerializerMethodField()
    user_reactions = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = '__all__'
        read_only_fields = ['reaction_summary', 'user_reactions', 'user', 'city']

    def get_reaction_summary(self, obj):
        from django.db.models import Count  # ensure it's imported

        summary = (
            obj.reactions.values('emoji')     # ✅ Group by emoji
            .annotate(count=Count('emoji'))   # ✅ Count each group
            .order_by('-count')
        )
        return {entry['emoji']: entry['count'] for entry in summary}


    def get_user_reactions(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if user and user.is_authenticated:
            return list(obj.reactions.filter(user=user).values_list('emoji', flat=True))
        return []


    def get_user_reactions(self, obj):
        user = self.context.get('request') and self.context['request'].user
        if user and user.is_authenticated:
            return list(obj.reactions.filter(user=user).values_list('emoji', flat=True))
        return []
    
class ReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reaction
        fields = ['post', 'emoji']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'content', 'link', 'created_at', 'is_read']

class ReportSerializer(serializers.ModelSerializer):
    content_snippet = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = '__all__'

    def get_content_snippet(self, obj):
        if obj.content_type == 'post':
            post = Post.objects.filter(id=obj.content_id).first()
            return post.content[:100] if post else None
        elif obj.content_type == 'marketplace':
            item = MarketplaceItem.objects.filter(id=obj.content_id).first()
            return item.description[:100] if item else None
        return None
