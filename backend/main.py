from fastapi import FastAPI
from app.api_endpoints import router as api_router
from app.routes.w2_routes import router as w2_router

app = FastAPI(title="Tax Filing API")

app.include_router(api_router, prefix="/api")
app.include_router(w2_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Tax Filing API is running"}
