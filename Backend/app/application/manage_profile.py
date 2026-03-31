from django.contrib.auth.models import User
from Backend.app.documents.models import Profile


def get_or_create_profile(user):
    """Retorna o perfil do usuário, criando se não existir."""
    profile, _ = Profile.objects.get_or_create(user=user, defaults={"role": "admin" if user.is_staff else "user"})
    return profile


def set_user_role(user_id, role):
    """Altera o papel de um usuário. Role: 'admin' ou 'user'."""
    if role not in ("admin", "user"):
        raise ValueError("Role inválido. Use 'admin' ou 'user'.")

    user = User.objects.get(pk=user_id)
    profile = get_or_create_profile(user)
    profile.role = role
    profile.save()

    # Sincroniza is_staff com o role
    user.is_staff = role == "admin"
    user.save()

    return profile


def list_users_with_profiles():
    """Retorna todos os usuários com seus perfis."""
    users = User.objects.select_related("profile").all()
    return [
        {
            "id":         u.id,
            "username":   u.username,
            "email":      u.email,
            "is_active":  u.is_active,
            "role":       u.profile.role if hasattr(u, "profile") else "user",
            "created_at": u.date_joined.strftime("%d/%m/%Y %H:%M"),
        }
        for u in users
    ]