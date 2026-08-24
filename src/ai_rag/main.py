from fastapi import FastAPI

from ai_rag.api.router import router as api_router


def create_app() -> FastAPI:

    app = FastAPI(title="AI RAG API", version="1.0.0")
    app.include_router(api_router)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "third test, Panda"}

    return app


app = create_app()
