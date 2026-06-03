import subprocess
from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="hi")
templates = Jinja2Templates(directory="templates")


@app.get("/")
def root():
    return RedirectResponse(url="/login")


@app.get("/login")
def login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


@app.get("/api/*")
def redirect_login():
    return RedirectResponse(url="/login")


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
    return RedirectResponse(url="/dashboard")


@app.post("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")
