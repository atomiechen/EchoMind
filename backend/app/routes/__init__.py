from fastapi import APIRouter

from . import users
from . import meetings


api_router = APIRouter()
api_router.include_router(users.api_router, tags=["users"])
api_router.include_router(meetings.api_router, tags=["meetings"])
