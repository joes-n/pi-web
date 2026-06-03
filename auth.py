import sys

import PAM  # system wide python3-pam on pi uses PAM instead of pam


def main():
    data = sys.stdin.read().splitlines()

    if len(data) != 2:
        return 1

    p = PAM.pam()

    username = data[0]
    password = data[1]

    if not p.authenticate(username, password, service="web"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
