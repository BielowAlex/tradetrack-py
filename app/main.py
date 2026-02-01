from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import mt5
from app.config import settings

app = FastAPI(
    title="TradeTrack MT5 Integration API",
    description="FastAPI backend for MetaTrader 5 integration via investor password",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mt5.router)


@app.get("/")
async def root():
    return {"message": "TradeTrack MT5 Integration API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
