"""Authentication & registration router."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, Token, LoginRequest
from app.services.auth_service import DUMMY_HASH, hash_password, verify_password, create_access_token
from app.services.rate_limit import client_ip, login_key, rate_limit
from app.services.seed_service import seed_default_pipeline_stages

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("register", 3, 3600, client_ip))],
)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        # Unique lower(email) index; same generic answer whatever the reason
        await db.rollback()
        raise HTTPException(status_code=409, detail="Could not register with these details")

    # Seed default pipeline stages in the same transaction (commits)
    await seed_default_pipeline_stages(db, user.id)
    await db.refresh(user)

    return user


@router.post("/login", response_model=Token, dependencies=[Depends(rate_limit("login", 5, 60, login_key))])
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not verify_password(body.password, user.hashed_password if user else DUMMY_HASH) or not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=token)


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
