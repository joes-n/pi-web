import json
import subprocess
from string import Template
from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_303_SEE_OTHER

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="hi")
templates = Jinja2Templates(directory="templates")


def get_ip():
    ip = subprocess.run(["hostname", "-I"], text=True, capture_output=True)
    return ip.stdout


def post_ip(payload):
    result = subprocess.run(
        ["sudo", "-n", "/usr/bin/python3", "/usr/local/libexec/netctl.py"],
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
    return JSONResponse(get_ip())


@app.post("/api/ip")
def post_api_ip(request: Request):
    username = request.session.get("user")
    if not username:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    post_ip(request)
    return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)


@app.get("/dashboard")
def dashboard(request: Request):
    username = request.session.get("user")
    if not username:
        return RedirectResponse(url="/login")

    return templates.TemplateResponse(
        request=request, name="dashboard.html", context={"ip": get_ip()}
    )
