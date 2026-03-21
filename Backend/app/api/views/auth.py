from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from Backend.app.api.factories import AuthFactory


class LoginView(APIView):
    """
    POST /api/auth/login/
    Autentica um administrador e retorna tokens JWT.
    Usa AuthFactory (Factory Method) para obter o caso de uso.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get("username", "")
        password = request.data.get("password", "")

        caso_de_uso = AuthFactory.make_login()

        try:
            resultado = caso_de_uso.executar(username, password)
            return Response(resultado, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except PermissionError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )