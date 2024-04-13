from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class ShipInspectionInput(BaseModel):
    inspection_location: str
    ship_name: str
    inspection_details: str
    numerical_value: int


class UserBase(BaseModel):
    username: str
    email: str
    password: str


class UserBase2(BaseModel):
    id: int
    username: str
    email: str
    password: str


class UserDisplay(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        from_attributes = True


class User(BaseModel):
    username: str

    class Config:
        from_attributes = True


class UserId(BaseModel):
    id: int

    class Config:
        from_attributes = True


class CommentBase(BaseModel):
    text: str
    timestamp: datetime
    user_id: int
    post_id: int


class CommentDisplay(BaseModel):
    id: int
    user: User
    post_id: int
    timestamp: datetime
    text: str

    class Config:
        from_attributes = True


class PostBase(BaseModel):
    image_url: str
    image_url_type: str
    caption: str
    creator_id: str  # id for user in Foreign key


class PostDisplay(BaseModel):
    id: int
    image_url: str
    image_url_type: str
    caption: str
    timestamp: datetime
    user: Optional[User] = None
    comments: List[CommentDisplay]

    class Config:
        from_attributes = True


class UserAuth(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        from_attributes = True
