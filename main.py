from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import init_db
from app.api.chat import router as chat_router
from app.api.leads import router as leads_router
from app.api.prospects import router as prospects_router
from app.api.leads_pdf import router as leads_pdf_router
from app.api.tracking import router as tracking_router
from app.api.monitoring import router as monitoring_router
from app.api.subscriptions import router as subscriptions_router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()   # Crée les tables au démarrage
    yield


app = FastAPI(
    title="Assistant IA Immobilier",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(leads_router)
app.include_router(prospects_router)
app.include_router(leads_pdf_router)
app.include_router(tracking_router)
app.include_router(monitoring_router)
app.include_router(subscriptions_router)


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.environment}
