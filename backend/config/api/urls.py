from django.urls import path,include
from .views import CustomTokenView, DashboardView,PensionProcessView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter
from accounts.views import RoleViewSet, UserViewSet


router = DefaultRouter()
router.register("roles", RoleViewSet, basename="roles")
router.register("users", UserViewSet, basename="users")

urlpatterns = [
    path('login/', CustomTokenView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Dashboard API
    path('dashboard/', DashboardView.as_view()),

    # Pension Process API
    path('pension/process/', PensionProcessView.as_view()),

    path('users/me/', UserViewSet.as_view({'get': 'me'}), name='user-me'),
    path('', include(router.urls)),
]