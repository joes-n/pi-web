from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from auth import check_pam

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="hi")
templates = Jinja2Templates(directory="templates")


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

    if check_pam(username, password):
        return RedirectResponse("/dashboard", status_code=300)

    return templates.TemplateResponse(
        request=request, name="login.html", context={"error": "wrong"}, status_code=401
    )


@app.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")
