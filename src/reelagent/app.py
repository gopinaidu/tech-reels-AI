from fastapi import FastAPI

app = FastAPI(title="ReelAgent", version="0.1.0")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
