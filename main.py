import ipaddress
import json
import subprocess
from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_303_SEE_OTHER

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="hi")
templates = Jinja2Templates(directory="templates")


app.mount("/static", StaticFiles(directory="static"), name="static")


def run_nmcli(args: list[str], check: bool = True):
    result = subprocess.run(
        ["nmcli", *args],
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "nmcli failed"
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


def prefix_to_netmask(prefix: int):
    return str(ipaddress.IPv4Network(f"0.0.0.0/{prefix}").netmask)


def split_addresses(value: str):
    return value.replace(",", " ").split()


def get_eth0_config():
    config = {
        "connection": "",
        "ip": "",
        "prefix": "",
        "netmask": "",
        "gateway": "",
        "dns": "",
        "error": "",
    }

    try:
        connection = eth_connection_name()
        config["connection"] = connection

        addresses = get_connection_field(connection, "ipv4.addresses")
        if addresses:
            first_address = addresses.split(",", 1)[0].strip()
            if "/" in first_address:
                ip_value, prefix_value = first_address.rsplit("/", 1)
                prefix = int(prefix_value)
                config["ip"] = str(ipaddress.IPv4Address(ip_value))
                config["prefix"] = str(prefix)
                config["netmask"] = prefix_to_netmask(prefix)

        gateway = get_connection_field(connection, "ipv4.gateway")
        if gateway:
            config["gateway"] = str(ipaddress.IPv4Address(gateway))

        dns = get_connection_field(connection, "ipv4.dns")
        if dns:
            config["dns"] = ", ".join(
                str(ipaddress.IPv4Address(value)) for value in split_addresses(dns)
            )
    except Exception as exc:
        config["error"] = str(exc)

    return config


def netctl(payload):
    result = subprocess.run(
        ["sudo", "-n", "/usr/bin/python3", "/usr/local/libexec/netctl.py"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )
    return result


def change_account(payload):
    result = subprocess.run(
        ["sudo", "-n", "/usr/bin/python3", "/usr/local/libexec/change_acct.py"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )
    return result


@app.get("/")
def root():
    return RedirectResponse(url="/login")


@app.get("/login")
def login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


@app.post("/api/login")
def post_login(
    request: Request, username: Annotated[str, Form()], password: Annotated[str, Form()]
):
    check = subprocess.run(
        ["sudo", "-n", "/usr/bin/python3", "/usr/local/libexec/auth.py"],
        input=f"{username}\n{password}\n",
        text=True,
    )
    if check.returncode != 0:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "wrong"},
            status_code=401,
        )
    request.session["user"] = username
    return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)


@app.post("/api/logout")
def post_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)


@app.get("/api/ip")
def get_api_ip():
    return JSONResponse(get_eth0_config())


@app.post("/api/ip")
def post_api_ip(
    request: Request,
    ip: Annotated[str, Form()] = "",
    prefix: Annotated[str, Form()] = "",
    gateway: Annotated[str, Form()] = "",
    dns: Annotated[str, Form()] = "",
):
    username = request.session.get("user")
    if not username:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    payload = {}
    if ip.strip():
        payload["ip"] = ip.strip()
    if prefix.strip():
        payload["prefix"] = prefix.strip()
    if gateway.strip():
        payload["gateway"] = gateway.strip()
    if dns.strip():
        payload["dns"] = dns.strip()

    if not payload:
        request.session["message"] = "No network settings changed"
        return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)

    result = netctl(payload)

    if result.returncode != 0:
        request.session["message"] = result.stderr.strip() or "Network change failed"
        return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)
    request.session["message"] = result.stdout.strip() or "Network settings updated"
    return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)


@app.post("/api/account")
def post_api_account(
    request: Request,
    current_password: Annotated[str, Form()],
    new_username: Annotated[str, Form()] = "",
    new_password: Annotated[str, Form()] = "",
):
    username = request.session.get("user")
    if not username:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    new_username = new_username.strip()
    if not new_username and not new_password:
        request.session["message"] = "No account settings changed"
        return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)

    check = subprocess.run(
        ["sudo", "-n", "/usr/bin/python3", "/usr/local/libexec/auth.py"],
        input=f"{username}\n{current_password}\n",
        text=True,
    )
    if check.returncode != 0:
        request.session["message"] = "Current password is wrong"
        return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)

    payload = {"current_username": username}
    if new_username:
        payload["new_username"] = new_username
    if new_password:
        payload["new_password"] = new_password

    result = change_account(payload)
    if result.returncode != 0:
        request.session["message"] = result.stderr.strip() or "Account change failed"
        return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)

    request.session["user"] = new_username or username
    request.session["message"] = result.stdout.strip() or "Account updated"
    return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)


@app.get("/dashboard")
def dashboard(request: Request):
    username = request.session.get("user")
    if not username:
        return RedirectResponse(url="/login")
    message = request.session.pop("message", None)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "network": get_eth0_config(),
            "message": message,
            "username": username,
        },
    )
