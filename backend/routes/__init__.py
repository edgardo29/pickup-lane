# Re-export routers here so the main FastAPI app can include feature routes
# from one place as the API grows.
from backend.routes.user_routes import router as users_router

__all__ = ["users_router"]
