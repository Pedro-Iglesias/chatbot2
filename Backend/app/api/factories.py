

from Backend.app.application.login_admin import LoginAdmin
from Backend.app.application.delete_document import DeleteDocument
from Backend.app.infrastructure.repositories.sql.postgres_document_repository import (
    PostgresDocumentRepository,
)


class AuthFactory:
    @staticmethod
    def make_login() -> LoginAdmin:
        return LoginAdmin()


class DocumentFactory:
    @staticmethod
    def make_delete() -> DeleteDocument:
        repository = PostgresDocumentRepository()
        return DeleteDocument(repository=repository)