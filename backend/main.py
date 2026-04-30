from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import check_database_connection
from backend.routes import (
    user_payment_method_router,
    user_settings_router,
    users_router,
    venues_router,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Backend is running"}


@app.get("/db-health")
def db_health():
    check_database_connection()
    return {"message": "Database connection is working"}


# Include feature-specific routers here so the main app stays small as the API
# surface grows.
app.include_router(users_router)
app.include_router(user_settings_router)
app.include_router(user_payment_method_router)
app.include_router(venues_router)
