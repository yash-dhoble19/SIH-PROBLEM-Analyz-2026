"""
API router package.
"""

from platform_core.api.routes_problems import router as problems_router
from platform_core.api.routes_analysis import router as analysis_router
from platform_core.api.routes_admin import router as admin_router

__all__ = ["problems_router", "analysis_router", "admin_router"]
