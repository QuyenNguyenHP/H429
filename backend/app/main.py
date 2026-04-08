from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import alarms, live, system, trends
from app.config import APP_NAME, APP_VERSION, CORS_ORIGINS
from app.db import engine
from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(live.router)
app.include_router(trends.router)
app.include_router(alarms.router)
app.include_router(system.router)


@app.get("/")
def root():
    return {"name": APP_NAME, "version": APP_VERSION, "status": "running"}
