import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.api.v1 import websocket_routes
from src.core.config import get_config
from src.core.logger import logger, shutdown_logging

templates = Jinja2Templates(directory="src/templates")


settings = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Configuration loaded: {settings}")
    env = settings.ENV
    log_level = settings.LOG_LEVEL
    app_name = settings.APP_NAME
    logger.info(f"Starting {app_name} in {env} environment with LOG LEVEL = {log_level}")
    yield
    logger.info(f"Shutting down {app_name}")
    await shutdown_logging()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.LOG_LEVEL == "DEBUG",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None
)


from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or list of specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get(settings.BASE_URL + "/login", include_in_schema=False, response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "base_url": settings.BASE_URL})


# Login POST endpoint: validates credentials and then redirects with them in the URL.
@app.post(settings.BASE_URL + "/login", include_in_schema=False)
async def login(username: str = Form(...), password: str = Form(...)):
    correct_username = os.getenv("SWAGGER_USERNAME", "")
    correct_password = os.getenv("SWAGGER_PASSWORD", "")
    
    logger.info(f"Correct username: {correct_username}, Correct password: {correct_password}")
    
    if correct_username == "" or correct_password == "":
        raise HTTPException(status_code=500, detail="Swagger cannot be accessed right now")
    
    if username == correct_username and password == correct_password:
        # Redirect to docs with credentials in query parameters (stateless authentication)
        return RedirectResponse(url=f"{settings.BASE_URL}/docs?username={username}&password={password}", status_code=302)
    else:
        raise HTTPException(status_code=401, detail="Invalid username or password")

# Swagger docs endpoint that validates credentials on every request using query parameters.
@app.get(settings.BASE_URL + "/docs", include_in_schema=False)
async def get_swagger_documentation(username: str = Query(None), password: str = Query(None)):
    correct_username = settings.SWAGGER_USERNAME
    correct_password = settings.SWAGGER_PASSWORD

    logger.info(f"Correct username: {correct_username}, Correct password: {correct_password}")
    
    if correct_username == "" or correct_password == "":
        raise HTTPException(status_code=500, detail="Swagger cannot be accessed right now")
    
    if username != correct_username or password != correct_password:
        return RedirectResponse(url=settings.BASE_URL + "/login")
    
    openapi_url = app.openapi_url or "/openapi.json"
    return get_swagger_ui_html(openapi_url=openapi_url, title=app.title + " - Swagger UI")

@app.get(settings.BASE_URL + "/status", tags=["Service Status"])
async def status():
    response = {"message": "Good Day! Everything is up and running :)"}
    logger.info(f"Response sent: {response}")
    return response

app.include_router(websocket_routes.router, prefix=settings.BASE_URL, tags=["Chat WebSocket"])
