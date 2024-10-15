from fastapi import FastAPI
from app.routes import router
import uvicorn

app = FastAPI()

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app)