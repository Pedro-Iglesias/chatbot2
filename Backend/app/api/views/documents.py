"""
View para operações sobre documentos.
Usa DocumentFactory (Factory Method) para obter o caso de uso.
Requer autenticação JWT — apenas administradores podem excluir documentos.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from Backend.app.api.factories import DocumentFactory


class DocumentDeleteView(APIView):
    """
    DELETE /api/documents/<id>/
    Exclui um documento e todos os seus chunks do banco de dados.
    Requer token JWT de administrador no header:
        Authorization: Bearer <access_token>
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def delete(self, request, id_documento: int):
        caso_de_uso = DocumentFactory.make_delete()

        try:
            resultado = caso_de_uso.executar(id_documento)
            return Response(resultado, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except LookupError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )