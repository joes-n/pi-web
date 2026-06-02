import pam


def check_pam(username: str, password: str):
    if not username or not password:
        return False

    p = pam.pam()

    return p.authenticate(username, password, service="login")
