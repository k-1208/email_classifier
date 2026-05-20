from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from service.llm_service import classify_email


app = FastAPI(
    title="Email Classification API",
    version="1.0.0"
)


DEFAULT_PORT = 8001


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://email-classifier-sigma.vercel.app/",
        "https://a31f-2401-4900-8fe2-aac9-2346-172c-c38f-c898.ngrok-free.app",
        "https://email-classifier-sigma.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# HEALTH CHECK
# =========================

@app.get("/health")
async def health():

    return {
        "status": "ok"
    }


# =========================
# WAKE ENDPOINT
# =========================

@app.post("/wake")
async def wake():

    try:
        result = await classify_email(
            "hello world"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        ) from exc

    return {
        "success": True,
        "result": result
    }


# =========================
# CLASSIFY ENDPOINT
# =========================

@app.post("/classify")
async def classify(payload: dict):

    email_text = payload.get(
        "email_text",
        ""
    )

    if not email_text:

        return {
            "success": False,
            "message": "email_text is required"
        }

    result = await classify_email(
        email_text
    )

    return {
        "success": True,
        "result": result
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=DEFAULT_PORT
    )