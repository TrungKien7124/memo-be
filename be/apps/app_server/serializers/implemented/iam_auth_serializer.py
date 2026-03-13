from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.app_server.validators.implemented.iam_validators import validate_password_strength

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        if User.objects.all_with_deleted().filter(email=value.lower()).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def validate_username(self, value):
        username = value.strip()
        if not username:
            raise serializers.ValidationError('Username is required.')
        if User.objects.all_with_deleted().filter(username__iexact=username).exists():
            raise serializers.ValidationError('A user with this username already exists.')
        return username

    def validate_password(self, value):
        return validate_password_strength(value)

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth import authenticate

        login_input = attrs['email'].strip()
        password = attrs['password']

        if not login_input:
            raise serializers.ValidationError({'email': 'Email or username is required.'})

        if '@' in login_input:
            user = User.objects.filter(email=login_input.lower(), is_deleted=False).first()
        else:
            user = User.objects.filter(username__iexact=login_input, is_deleted=False).first()

        if not user:
            raise serializers.ValidationError('Invalid email or password.')

        user = authenticate(email=user.email.lower(), password=password)
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('This account has been deactivated.')
        attrs['user'] = user
        return attrs


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }
