from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import RoleViewSet, UserViewSet
from .views import CustomTokenView, DashboardView, LogoutView, PensionProcessView


router = DefaultRouter()
router.register("roles", RoleViewSet, basename="roles")
router.register("users", UserViewSet, basename="users")

urlpatterns = [
    path('login/', CustomTokenView.as_view(), name='token_obtain_pair'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Dashboard API
    path('dashboard/', DashboardView.as_view()),

    # Pension Process API
    path('pension/process/', PensionProcessView.as_view()),

    path('users/me/', UserViewSet.as_view({'get': 'me'}), name='user-me'),
    path('', include(router.urls)),
]