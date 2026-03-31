# Re-exporta o model do app Django para manter a arquitetura em camadas
from Backend.app.documents.models import AdminLog

__all__ = ["AdminLog"]