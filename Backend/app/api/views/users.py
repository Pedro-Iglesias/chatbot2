from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth.models import User
from Backend.app.application.manage_profile import (
    list_users_with_profiles,
    set_user_role,
    get_or_create_profile,
)
from Backend.app.application.log_action import log_action


class UserListView(APIView):
    """
    GET /api/users/  → lista todos os usuários com seus perfis.
    Requer autenticação JWT e is_staff=True.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        try:
            users = list_users_with_profiles()
            return Response(users, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserRoleUpdateView(APIView):
    """
    PATCH /api/users/<id>/role/  → altera o papel de um usuário.

    Body JSON:
        { "role": "admin" }   ou   { "role": "user" }
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def patch(self, request, user_id: int):
        role = request.data.get("role", "").strip()

        if not role:
            return Response({"error": "O campo 'role' é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            profile = set_user_role(user_id, role)

            log_action(
                user=request.user,
                action="UPDATE",
                resource_type="user",
                resource_id=user_id,
                resource_name=profile.user.username,
                details=f"Role alterado para: {role}",
            )

            return Response({
                "id":       profile.user.id,
                "username": profile.user.username,
                "role":     profile.role,
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({"error": "Usuário não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MeView(APIView):
    """
    GET /api/users/me/  → retorna os dados do usuário autenticado.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = get_or_create_profile(user)
        return Response({
            "id":       user.id,
            "username": user.username,
            "email":    user.email,
            "role":     profile.role,
            "is_staff": user.is_staff,
        })