from fastapi import APIRouter

from app.api.routes import (
    accounting,
    auth,
    billing,
    companies,
    dashboard,
    demo,
    health,
    invoices,
    tax,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(dashboard.router)
api_router.include_router(invoices.router)
api_router.include_router(tax.router)
api_router.include_router(billing.router)
api_router.include_router(accounting.router)
api_router.include_router(demo.router)
api_router.include_router(health.router)

from app.api.routes import extension, portal
api_router.include_router(extension.router)
api_router.include_router(portal.router)
