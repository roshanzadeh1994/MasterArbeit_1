from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from db.database import Base, get_db
from db.database import engine
from routers import router,user_router
from auth import authentication

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Create engine and session
Base.metadata.create_all(bind=engine)

# Create Jinja2Templates instance
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


app.include_router(router.router)
app.include_router(user_router.router)
app.include_router(authentication.router)





