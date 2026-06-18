from src.db.models import User


def format_user_mention(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    return user.display_name
