from fastapi import FastAPI
def create_api()->FastAPI:
    app=FastAPI(title="AI Creative GIF Studio")
    @app.get("/health")
    async def health(): return {"status":"ok"}
    @app.get("/ready")
    async def ready(): return {"status":"ready"}
    return app
