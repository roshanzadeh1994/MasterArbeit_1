from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from db.database import Base, get_db
from db.database import engine
from routers import  user_router, router
from auth import authentication

app = FastAPI()

# Create engine and session


app.include_router(user_router.router)
app.include_router(router.router)
app.include_router(authentication.router)

Base.metadata.create_all(bind=engine)
