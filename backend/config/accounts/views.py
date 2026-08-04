from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet

from audit.services import log_audit

from .models import Role, UserProfile, UserRole
from .permissions import IsAdminRole
from .user_auth import build_user_auth_payload
from .serializers import (
    RoleSerializer,
    UserCreateSerializer,
    UserListSerializer,
    UserUpdateSerializer,
)

User = get_user_model()

USER_AUDIT_TABLE = "accounts_user"
USER_AUDIT_MODULE = "USER_MANAGEMENT"


def _attach_active_role(queryset):
    users = list(queryset)
    user_ids = [u.id for u in users]
    assignments = (
        UserRole.objects.filter(user_id__in=user_ids, is_active=True, role__is_active=True)
        .select_related("role")
        .order_by("user_id", "id")
    )
    role_by_user = {}
    for assignment in assignments:
        role_by_user.setdefault(assignment.user_id, assignment.role)

    for user in users:
        user.active_role = role_by_user.get(user.id)
    return users


def _user_audit_snapshot(user):
    users = _attach_active_role([user])
    return UserListSerializer(users[0]).data


class RoleViewSet(ModelViewSet):
    queryset = Role.objects.all().order_by("name")
    serializer_class = RoleSerializer
    permission_classes = [IsAdminRole]

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"error": "Roles cannot be deleted. Deactivate instead."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class UserViewSet(ViewSet):
    permission_classes = [IsAdminRole]

    def list(self, request):
        queryset = User.objects.select_related("profile").order_by("username")
        users = _attach_active_role(queryset)
        serializer = UserListSerializer(users, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        user = User.objects.select_related("profile").filter(pk=pk).first()
        if not user:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        users = _attach_active_role([user])
        return Response(UserListSerializer(users[0]).data)

    def create(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        snapshot = _user_audit_snapshot(user)
        log_audit(
            request,
            table_name=USER_AUDIT_TABLE,
            record_id=user.id,
            action="CREATE",
            old_data=None,
            new_data=snapshot,
            module=USER_AUDIT_MODULE,
        )
        return Response(snapshot, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        user = User.objects.select_related("profile").filter(pk=pk).first()
        if not user:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        old_snapshot = _user_audit_snapshot(user)
        serializer = UserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.update(user, serializer.validated_data)
        user = User.objects.select_related("profile").get(pk=pk)
        new_snapshot = _user_audit_snapshot(user)
        log_audit(
            request,
            table_name=USER_AUDIT_TABLE,
            record_id=user.id,
            action="UPDATE",
            old_data=old_snapshot,
            new_data=new_snapshot,
            module=USER_AUDIT_MODULE,
        )
        return Response(new_snapshot)

    def me(self, request):
        return Response(build_user_auth_payload(request.user))
