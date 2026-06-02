import sys

import pam


def main():
    data = sys.stdin.read().splitlines()

    if len(data) != 2:
        return 1

    p = pam.pam()

    username = data[0]
    password = data[1]

    if not p.authenticate(username, password, service="web"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
