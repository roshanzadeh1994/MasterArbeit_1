from fastapi import FastAPI, Depends, HTTPException, Request
from db.database import Base, get_db
from db.database import engine
from routers import  user_router, router
from auth import authentication
from fastapi.staticfiles import StaticFiles

app = FastAPI()


app.mount("/static", StaticFiles(directory="templates"), name="static")

app.include_router(user_router.router)
app.include_router(router.router)
app.include_router(authentication.router)

Base.metadata.create_all(bind=engine)
