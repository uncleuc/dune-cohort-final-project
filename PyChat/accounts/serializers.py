from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import AccountProfile

User = get_user_model()


class AccountProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountProfile
        fields = ['id', 'bio', 'created_by', 'created_at']


class AccountSerializer(serializers.ModelSerializer):
    profile = AccountProfileSerializer(source='account_profile', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_staff', 'is_active', 'date_joined', 'profile']
        read_only_fields = ['id', 'date_joined', 'profile']


class AdminCreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'is_staff', 'is_active']
        read_only_fields = ['id']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        AccountProfile.objects.get_or_create(user=user, defaults={'created_by': self.context['request'].user})
        return user
