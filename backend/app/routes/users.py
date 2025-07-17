from typing_extensions import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter, Depends, HTTPException, status, Response

from app.models import (
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    SuccessResponse,
    Token,
    UserResponse,
)
from app.core.auth import encode_token
from app.deps import DependsUser, UserDep, UserManagerDep
from app.config import settings
from app.utils.log import get_logger


api_router = APIRouter()
logger = get_logger()


@api_router.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_manager: UserManagerDep,
) -> Token:
    user, _ = user_manager.authenticateUser(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = encode_token(str(user.user_id))
    return Token(access_token=access_token, token_type="bearer")


@api_router.post("/api/register")
async def register(
    register_request: RegisterRequest, user_manager: UserManagerDep
) -> RegisterResponse:
    username = register_request.username
    password = register_request.password
    code = user_manager.addUser(username, password)
    return RegisterResponse(code=code)


@api_router.post("/api/login")
async def login(
    login_request: RegisterRequest, response: Response, user_manager: UserManagerDep
) -> LoginResponse:
    username = login_request.username
    password = login_request.password
    user, code = user_manager.authenticateUser(username, password)
    if user:
        token = encode_token(str(user.user_id))
        response.set_cookie(
            key="mytoken",
            value=token,
            httponly=True,
            max_age=int(settings.access_token_expire.total_seconds()),
        )
    return LoginResponse(code=code)


@api_router.post("/api/checkLogin")
async def check_login(user: UserDep) -> UserResponse:
    logger.info("checklogin")
    return UserResponse(username=user.username)


@api_router.post("/api/logout", dependencies=[DependsUser])
async def logout(response: Response) -> SuccessResponse:
    response.delete_cookie(key="mytoken", httponly=True)
    return SuccessResponse()
