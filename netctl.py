import ipaddress
import json
import subprocess
import sys

ALLOWED_KEYS = {"ip", "prefix", "gateway", "dns"}


def run_nmcli(args: list[str], check: bool = True):
    result = subprocess.run(
        ["nmcli", *args],
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(message)
    return result


def parse_nmcli_line(line: str):
    fields = []
    current = []
    escaped = False

    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(char)

    fields.append("".join(current))
    return fields


def eth_connection_name():
    active = run_nmcli(
        [
            "--terse",
            "--fields",
            "NAME,TYPE,DEVICE",
            "connection",
            "show",
            "--active",
        ]
    ).stdout

    for line in active.splitlines():
        fields = parse_nmcli_line(line)
        if len(fields) == 3:
            name, conn_type, device = fields
            if conn_type == "802-3-ethernet" and device == "eth0":
                return name

    all_connections = run_nmcli(
        [
            "--terse",
            "--fields",
            "NAME,TYPE,DEVICE",
            "connection",
            "show",
        ]
    ).stdout

    ethernet_names = []
    for line in all_connections.splitlines():
        fields = parse_nmcli_line(line)
        if len(fields) != 3:
            continue

        name, conn_type, device = fields
        if conn_type == "802-3-ethernet":
            if device == "eth0":
                return name
            ethernet_names.append(name)

    if len(ethernet_names) == 1:
        return ethernet_names[0]

    raise RuntimeError("no NetworkManager connection profile found for eth0")


def get_connection_field(connection: str, field: str):
    return run_nmcli(
        ["--get-values", field, "connection", "show", connection]
    ).stdout.strip()


def current_config(connection: str):
    config: dict[str, object] = {
        "ip": None,
        "prefix": None,
        "gateway": None,
        "dns": [],
    }

    addresses = get_connection_field(connection, "ipv4.addresses")
    if addresses:
        first_address = addresses.split(",", 1)[0].strip()
        if "/" in first_address:
            ip_value, prefix_value = first_address.rsplit("/", 1)
            config["ip"] = str(ipaddress.IPv4Address(ip_value))
            config["prefix"] = int(prefix_value)

    gateway = get_connection_field(connection, "ipv4.gateway")
    if gateway:
        config["gateway"] = str(ipaddress.IPv4Address(gateway))

    dns = get_connection_field(connection, "ipv4.dns")
    if dns:
        config["dns"] = [
            str(ipaddress.IPv4Address(value)) for value in dns.replace(",", " ").split()
        ]

    return config


def validate_payload(raw: object):
    if not isinstance(raw, dict):
        raise ValueError("payload must be a JSON object")

    unknown = set(raw) - ALLOWED_KEYS
    if unknown:
        raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))}")

    payload: dict[str, object] = {}

    if "ip" in raw:
        payload["ip"] = str(ipaddress.IPv4Address(str(raw["ip"]).strip()))

    if "prefix" in raw:
        prefix = int(str(raw["prefix"]).strip())
        if prefix < 1 or prefix > 32:
            raise ValueError("prefix must be between 1 and 32")
        payload["prefix"] = prefix

    if "gateway" in raw:
        payload["gateway"] = str(ipaddress.IPv4Address(str(raw["gateway"]).strip()))

    if "dns" in raw:
        dns_raw = raw["dns"]
        if isinstance(dns_raw, str):
            values = dns_raw.replace(",", " ").split()
        elif isinstance(dns_raw, list):
            values = dns_raw
        else:
            raise ValueError("dns must be a string or list")

        if not values:
            raise ValueError("dns must include at least one address")
        payload["dns"] = [
            str(ipaddress.IPv4Address(str(value).strip())) for value in values
        ]

    return payload


def apply_config(connection: str, config: dict[str, object]):
    ip_value = config.get("ip")
    prefix_value = config.get("prefix")

    if ip_value is None or prefix_value is None:
        raise RuntimeError(
            "ip and prefix are required before applying a manual eth0 address"
        )

    args = [
        "connection",
        "modify",
        connection,
        "ipv4.method",
        "manual",
        "ipv4.addresses",
        f"{ip_value}/{prefix_value}",
    ]

    gateway = config.get("gateway")
    if gateway:
        args.extend(["ipv4.gateway", str(gateway)])

    dns = config.get("dns")
    if dns:
        args.extend(["ipv4.dns", " ".join(str(value) for value in dns)])

    run_nmcli(args)

    run_nmcli(["connection", "down", connection], check=False)
    up = run_nmcli(["connection", "up", connection], check=False)
    if up.returncode != 0:
        message = (
            up.stderr.strip()
            or up.stdout.strip()
            or f"saved settings, but eth0 did not activate"
        )
        raise RuntimeError(f"saved settings, but eth0 did not activate: {message}")


def main():
    try:
        raw = json.load(sys.stdin)
        changes = validate_payload(raw)
        if not changes:
            raise ValueError("payload must include at least one network setting")

        connection = eth_connection_name()
        config = current_config(connection)
        config.update(changes)
        apply_config(connection, config)
        print(f"Updated {connection}")
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
