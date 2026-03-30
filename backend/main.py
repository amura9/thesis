from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.settings import ensure_dirs
from backend.api import datasets, configs, evaluation, postprocessing, results #rights,

def create_app() -> FastAPI:
    ensure_dirs()
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], #else limit the allow origins: ["http://localhost:5173", "http://127.0.0.1:5173"]
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request, call_next):
        print("INCOMING:", request.method, request.url.path)
        return await call_next(request)

    app.include_router(datasets.router)
    app.include_router(configs.configs_router)
    app.include_router(configs.rights_router)
    app.include_router(postprocessing.router)
    #app.include_router(rights.router)
    app.include_router(evaluation.router)
    app.include_router(results.router)
    
    return app

app = create_app()
