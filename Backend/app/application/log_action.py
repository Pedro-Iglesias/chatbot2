from Backend.app.documents.models import AdminLog


def log_action(user, action, resource_type="", resource_id=None, resource_name="", details=""):
    """
    Registra uma ação administrativa no banco de dados.

    Parâmetros:
        user          — request.user (objeto User do Django)
        action        — "LOGIN" | "LOGOUT" | "CREATE" | "UPDATE" | "DELETE" | "REINDEX"
        resource_type — tipo do recurso, ex: "document"
        resource_id   — ID do recurso afetado
        resource_name — nome/título legível do recurso
        details       — informações extras (opcional)
    """
    AdminLog.objects.create(
        user=user,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        details=details,
    )