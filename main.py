from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.redis import check_redis_connection, close_redis_connection
from app.database.session import AsyncSessionLocal, engine
from app.database.base import Base
from app.middleware.csrf_middleware import CSRFMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware

from app.modules.auth.repository import seed_roles
from app.modules.auth.router import router as auth_router
from app.modules.auth.router import router_author as author_router
from app.modules.records.router import router as records_router
from app.modules.dashboard.router import router as dashboard_router

app = FastAPI()


origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        
    allow_credentials=True,
    allow_methods=["*"],          
    allow_headers=["*"],          
)

# Add your existing middleware
app.add_middleware(CSRFMiddleware)
app.add_middleware(RateLimitMiddleware)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await check_redis_connection()

    async with AsyncSessionLocal() as db:
        await seed_roles(db)


@app.on_event("shutdown")
async def shutdown():
    await close_redis_connection()

app.include_router(auth_router)
app.include_router(author_router)
app.include_router(records_router)
app.include_router(dashboard_router)
