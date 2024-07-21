from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from starlette.middleware.cors import CORSMiddleware

from src.auth.router import router as auth_router
from src.config import app_configs, settings
from src.external_service.router import router as external_service_router

from src.twitter.router import router as twitter_router

# Narratives router
from src.twitter.routers.narratives.router import router as narratives_router

# KOL clusters router
from src.twitter.routers.kol.router import router as kol_router

# Search term router
from src.twitter.routers.search.router import router as search_project_router

# User overview
from src.twitter.routers.overview.router import router as overview_router

app = FastAPI(**app_configs)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGINS_REGEX,
    allow_credentials=True,
    allow_methods=("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"),
    allow_headers=settings.CORS_HEADERS,
)


@app.get("/healthcheck", include_in_schema=False)
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Process errors or customize the response as needed here
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Could not process the request."},
    )


app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(
    external_service_router, prefix="/external-service", tags=["External Service Calls"]
)
app.include_router(
    twitter_router, prefix="/twitter", tags=["Twitter"]
)
app.include_router(
    narratives_router, prefix="/narratives", tags=["Narratives"]
)
app.include_router(
    kol_router, prefix="/kols", tags=["KOLs"]
)
app.include_router(
    search_project_router, prefix="/search", tags=["search project"]
)
app.include_router(
    overview_router, prefix="/twitter_users", tags=["Project overview"]
)
