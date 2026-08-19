from fastapi import FastAPI
from database import init_db

app = FastAPI(title="Coffee Log Web")

@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Coffee Log Web API"}
