import json
import re
import subprocess
import sys


ALLOWED_KEYS = {"current_username", "new_username", "new_password"}
USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
LOGIN_GROUP = "login"
BLOCKED_USERS = {"root", "webapp"}


def run(args: list[str], input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        input=input_text,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"{args[0]} failed"
        raise RuntimeError(message)
    return result


def user_exists(username: str) -> bool:
    result = subprocess.run(
        ["id", "-u", username],
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def validate_username(username: object, field: str) -> str:
    value = str(username).strip()
    if not USERNAME_RE.fullmatch(value):
        raise ValueError(f"{field} is not a valid Linux username")
    if value in BLOCKED_USERS:
        raise ValueError(f"{field} cannot be {value}")
    return value


def validate_password(password: object) -> str:
    value = str(password)
    if "\n" in value or "\r" in value:
        raise ValueError("password cannot contain newlines")
    if len(value) < 8:
        raise ValueError("password must be at least 8 characters")
    return value


def ensure_login_user(username: str) -> None:
    if not user_exists(username):
        raise ValueError("current user does not exist")

    groups = run(["id", "-nG", username]).stdout.split()
    if LOGIN_GROUP not in groups:
        raise ValueError(f"{username} is not in the {LOGIN_GROUP} group")


def validate_payload(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ValueError("payload must be a JSON object")

    unknown = set(raw) - ALLOWED_KEYS
    if unknown:
        raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))}")

    current_username = validate_username(raw.get("current_username", ""), "current_username")
    ensure_login_user(current_username)

    payload = {"current_username": current_username}

    new_username = str(raw.get("new_username", "")).strip()
    if new_username:
        new_username = validate_username(new_username, "new_username")
        if new_username != current_username and user_exists(new_username):
            raise ValueError("new username already exists")
        payload["new_username"] = new_username

    if "new_password" in raw and str(raw["new_password"]):
        payload["new_password"] = validate_password(raw["new_password"])

    if "new_username" not in payload and "new_password" not in payload:
        raise ValueError("payload must include new_username or new_password")

    return payload


def apply_change(payload: dict[str, str]) -> str:
    current_username = payload["current_username"]
    final_username = payload.get("new_username", current_username)

    if final_username != current_username:
        run(["usermod", "-l", final_username, current_username])

    if "new_password" in payload:
        run(["chpasswd"], input_text=f"{final_username}:{payload['new_password']}\n")

    return final_username


def main() -> int:
    try:
        payload = validate_payload(json.load(sys.stdin))
        username = apply_change(payload)
        print(f"Updated account {username}")
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
