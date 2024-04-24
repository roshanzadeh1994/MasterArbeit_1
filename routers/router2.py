# authentication.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.orm.session import Session
from db import models
from db.database import get_db
from db.hash import Hash
from auth import oauth2
from db.models import DbUser
from schemas import UserAuth, UserBase
from fastapi import FastAPI, Request
from db.db_user import create_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/login")
def login(request: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.DbUser).filter(models.DbUser.username == request.username).first()
    if not user or not Hash.verify(user.password, request.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    access_token = oauth2.create_access_token(data={"sub": request.username})
    return {"access_token": access_token, "token_type": "bearer", "user": user.username}


@router.get("/", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/signup", response_class=HTMLResponse)
async def signup(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


@router.post("/signup", response_model=UserBase)
def create_new_user(user: UserBase, db: Session = Depends(get_db)):
    new_user = create_user(db=db, request=UserBase(username=user.username, email=user.email, password=Hash.bcrypt(user.password)))
    return new_user
