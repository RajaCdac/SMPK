from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user

        # get role (adjust based on your model)
        role = user.userrole_set.first().role.name if user.userrole_set.exists() else "User"

        data["user"] = {
            "username": user.username,
            "role": role
        }

        return data


class CustomTokenView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer



