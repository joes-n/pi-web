import sys

import PAM  # system wide python3-pam on pi uses PAM instead of pam


def main():
    data = sys.stdin.read().splitlines()

    if len(data) != 2:
        return 1

    def conversation(auth, query_list, user_data):
        responses = []

        for query, query_type in query_list:
            if (
                query_type == PAM.PAM_PROMPT_ECHO_ON
            ):  # pam asks for visible input (username)
                responses.append((username, 0))

            elif (
                query_type == PAM.PAM_PROMPT_ECHO_OFF
            ):  # pam asks for hidden input (password)
                responses.append((password, 0))

            elif query_type in (
                PAM.PAM_TEXT_INFO,
                PAM.PAM_ERROR_MSG,
            ):  # pam shows message
                responses.append(("", 0))

            else:
                return None

        return responses

    username = data[0]
    password = data[1]

    try:
        p = PAM.pam()
        p.start("webapp")
        p.set_item(PAM.PAM_USER, username)
        p.set_item(PAM.PAM_CONV, conversation)

        return 0

    except PAM.error or Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())
