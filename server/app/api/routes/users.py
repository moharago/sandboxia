from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.config import supabase

router = APIRouter()


class UserCreate(BaseModel):
    email: str
    name: str
    company: Optional[str] = None
    phone: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None


@router.post("/users")
async def create_user(user: UserCreate):
    result = supabase.table("users").insert({
        "email": user.email,
        "name": user.name,
        "company": user.company,
        "phone": user.phone
    }).execute()
    
    return result.data[0]


@router.get("/users/{user_id}")
async def get_user(user_id: str):
    result = supabase.table("users")\
        .select("*")\
        .eq("id", user_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return result.data[0]


@router.patch("/users/{user_id}")
async def update_user(user_id: str, user: UserUpdate):
    update_data = {k: v for k, v in user.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    result = supabase.table("users")\
        .update(update_data)\
        .eq("id", user_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return result.data[0]