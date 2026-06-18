import secrets

INVITE_CODE_LENGTH = 8


def generate_invite_code() -> str:
    return secrets.token_hex(INVITE_CODE_LENGTH // 2).upper()


def normalize_invite_code(code: str) -> str:
    return code.strip().upper()
