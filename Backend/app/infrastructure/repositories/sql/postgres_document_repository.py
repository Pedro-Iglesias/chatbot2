"""
Implementação PostgreSQL do repositório de documentos.
Repository Pattern — ConcreteRepository usando Django ORM + PostgreSQL.
"""

from Backend.app.domain.repositories.document_repository import DocumentRepository
from Backend.app.documents.models import Documento, ChunkDocumento


class PostgresDocumentRepository(DocumentRepository):

    def get_by_id(self, id_documento: int):
        try:
            return Documento.objects.get(id=id_documento)
        except Documento.DoesNotExist:
            return None

    def delete(self, id_documento: int) -> bool:
        documento = self.get_by_id(id_documento)

        if documento is None:
            return False

        # Remove os chunks vinculados e depois o documento
        # (cascade já está configurado no model, mas explicitamos por clareza)
        ChunkDocumento.objects.filter(documento=documento).delete()
        documento.delete()

        return True

    def list_all(self) -> list:
        return list(
            Documento.objects.all().values(
                "id", "nome", "tipo", "caminho_arquivo", "indexado_em"
            )
        )