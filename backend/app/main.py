from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
import uvicorn

from app.config import settings
from app.routes import api_router
from app.sio import sio
from app.utils import SinglePageApplication, init_logging, get_logger
from app.core.db import init_db


# Initialize logging
init_logging()
logger = get_logger()


# for generating the operationId in openapi.json
def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


app = FastAPI(
    description="EchoMind - Backend",
    generate_unique_id_function=custom_generate_unique_id,
)

# register the API router
# this will automatically generate the OpenAPI schema and Swagger UI
app.include_router(api_router)

# integrate the Socket.IO server
sio.integrate(app)

# register CORS middleware
app.add_middleware(
    CORSMiddleware,
    # cannot set allow_origins to ["*"], otherwise cookies cannot be sent
    # allow_origins=[],
    # allow localhost for development
    allow_origin_regex=r"http://localhost(:\d*)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.spa_path:
    settings.spa_path = settings.spa_path.resolve()
    if settings.spa_path.is_dir():
        # mount the Single Page Application (SPA) if spa_path is set
        # this will serve the SPA from the specified directory
        app.mount(
            path="/", app=SinglePageApplication(directory=settings.spa_path), name="SPA"
        )
        logger.info(f"Serving frontend SPA mounted at {settings.spa_path}")
    else:
        logger.warning(
            f"SPA path ({settings.spa_path}) is not a directory, skipping serving the frontend."
        )
else:
    logger.info("SPA path is not set, skipping serving the frontend.")


if __name__ == "__main__":
    # initialize the database if not ready
    init_db()

    # start the FastAPI application with uvicorn in production mode
    # forwarded_allow_ips: allow reading the header set by nginx to show the real client IP in logs
    # timeout_graceful_shutdown: prevent long connections from blocking the service from stopping
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        forwarded_allow_ips="*",
        timeout_graceful_shutdown=2,
    )
