from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import Role, UserProfile, UserRole

User = get_user_model()


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name", "code", "is_active"]
        read_only_fields = ["code"]


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "emp_code",
            "designation",
            "department",
            "mobile_no",
        ]


class UserListSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    role_id = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()
    role_code = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "is_active",
            "profile",
            "role_id",
            "role_name",
            "role_code",
            "date_joined",
        ]

    def get_display_name(self, obj):
        name = obj.get_full_name().strip()
        return name or obj.username

    def get_profile(self, obj):
        profile = getattr(obj, "profile", None)
        if profile is None:
            return None
        return UserProfileSerializer(profile).data

    def get_role_id(self, obj):
        role = getattr(obj, "active_role", None)
        return role.id if role else None

    def get_role_name(self, obj):
        role = getattr(obj, "active_role", None)
        return role.name if role else None

    def get_role_code(self, obj):
        role = getattr(obj, "active_role", None)
        return role.code if role else None


class UserCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    role_id = serializers.IntegerField()
    emp_code = serializers.CharField(required=False, allow_blank=True, max_length=50)
    designation = serializers.CharField(required=False, allow_blank=True, max_length=100)
    department = serializers.CharField(required=False, allow_blank=True, max_length=100)
    mobile_no = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_role_id(self, value):
        if not Role.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid or inactive role.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        role_id = validated_data.pop("role_id")
        password = validated_data.pop("password")
        profile_fields = {
            "emp_code": validated_data.pop("emp_code", ""),
            "designation": validated_data.pop("designation", ""),
            "department": validated_data.pop("department", ""),
            "mobile_no": validated_data.pop("mobile_no", ""),
        }

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=password,
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        UserProfile.objects.create(user=user, **profile_fields)
        UserRole.objects.filter(user=user).update(is_active=False)
        UserRole.objects.create(user=user, role_id=role_id, is_active=True)
        return user


class UserUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    is_active = serializers.BooleanField(required=False)
    role_id = serializers.IntegerField(required=False)
    password = serializers.CharField(
        required=False, allow_blank=True, write_only=True, min_length=6
    )
    emp_code = serializers.CharField(required=False, allow_blank=True, max_length=50)
    designation = serializers.CharField(required=False, allow_blank=True, max_length=100)
    department = serializers.CharField(required=False, allow_blank=True, max_length=100)
    mobile_no = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate_role_id(self, value):
        if value is not None and not Role.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid or inactive role.")
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        if "email" in validated_data:
            instance.email = validated_data["email"]
        if "first_name" in validated_data:
            instance.first_name = validated_data["first_name"]
        if "last_name" in validated_data:
            instance.last_name = validated_data["last_name"]
        if "is_active" in validated_data:
            instance.is_active = validated_data["is_active"]

        password = validated_data.pop("password", None)
        if password:
            instance.set_password(password)
        instance.save()

        profile, _ = UserProfile.objects.get_or_create(user=instance)
        for field in ("emp_code", "designation", "department", "mobile_no"):
            if field in validated_data:
                setattr(profile, field, validated_data[field])
        profile.save()

        role_id = validated_data.get("role_id")
        if role_id is not None:
            UserRole.objects.filter(user=instance).update(is_active=False)
            UserRole.objects.update_or_create(
                user=instance,
                role_id=role_id,
                defaults={"is_active": True},
            )

        return instance
