from fastapi import FastAPI

app = FastAPI(title="Brewbot")

@app.get("/")
def root():
    return {"status": "Brewbot is running"}
