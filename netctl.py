import subprocess


def main(args: list[str]):

    result = subprocess.run(["nmcli", *args], text=True, capture_output=True)

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()
