from rest_framework import serializers
from .models import Post, Event, User, Notification
from .models import MarketplaceItem, SwappOffer, Feedback, Group, Message
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Report

class GroupSerializer(serializers.ModelSerializer):
    is_member = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = '__all__'

    def get_is_member(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and obj.members.filter(id=user.id).exists()

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'

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

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'city']

class EventSerializer(serializers.ModelSerializer):
    rsvps = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ['host']
        
class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'type', 'content', 'created_at']

class MarketplaceItemSerializer(serializers.ModelSerializer):
    is_saved = serializers.SerializerMethodField()
    fields = [..., 'swapp_wishlist']
    class Meta:
        model = MarketplaceItem
        fields = [..., 'is_saved']  # include existing fields

    def get_is_saved(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.saved_by.filter(id=user.id).exists()
        return False
    class Meta:
        model = MarketplaceItem
        fields = [..., 'delivery_options', 'delivery_note']


class SwappOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = SwappOffer
        fields = '__all__'
        read_only_fields = ['offered_by', 'status', 'date_created', 'is_seen']

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'city', 'is_business']  # exclude email!
    
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'content', 'link', 'created_at', 'is_read']