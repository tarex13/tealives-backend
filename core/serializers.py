from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (
    User, Post, Event, Notification, MarketplaceItem,
    SwappOffer, Feedback, Group, Message, Comment, Report
)

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
        fields = ['username', 'email', 'bio', 'city', 'profile_image']
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

class MarketplaceItemSerializer(serializers.ModelSerializer):
    is_saved = serializers.SerializerMethodField()
    saved_by_user = serializers.SerializerMethodField()

    class Meta:
        model = MarketplaceItem
        fields = [
            'id', 'title', 'description', 'price',
            'delivery_options', 'delivery_note',
            'is_saved', 'saved_by_user',
            # Add more fields as needed
        ]

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

class GroupSerializer(serializers.ModelSerializer):
    is_member = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = '__all__'

    def get_is_member(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and obj.members.filter(id=user.id).exists()

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'type', 'content', 'created_at']

# -----------------------------
# Notifications & Reports
# -----------------------------

ALLOWED_REACTIONS = ['👍', '❤️', '😂']

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = '__all__'

    def validate_reactions(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Reactions must be a dictionary.")
        for emoji in value.keys():
            if emoji not in ALLOWED_REACTIONS:
                raise serializers.ValidationError(f"Invalid reaction emoji: {emoji}")
        return value

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
