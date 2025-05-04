"""Main FastAPI application setup."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.database import create_db_and_tables
from app.routes import auth, game, inventory

app = FastAPI(title="Rogue-like Game API")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(inventory.router)
app.include_router(auth.router)
app.include_router(game.router)

@app.on_event("startup")
def on_startup():
    """Initialize database on startup."""
    create_db_and_tables()

@app.get("/")
async def root_redirect():
    """Redirect root to static index.html."""
    return RedirectResponse(url="/static/index.html")
