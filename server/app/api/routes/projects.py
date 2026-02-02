from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.core.config import supabase

router = APIRouter()


class ProjectStatusUpdate(BaseModel):
    status: int
    current_step: Optional[int] = None


class DraftSave(BaseModel):
    step: str
    data: dict


class TrackSelect(BaseModel):
    track: str


class QuickCheckResult(BaseModel):
    result: str


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    result = supabase.table("projects")\
        .select("*")\
        .eq("id", project_id)\
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    return result.data[0]


@router.get("/projects/{project_id}/files")
async def get_project_files(project_id: str):
    """프로젝트에 업로드된 파일 목록 조회"""
    result = supabase.table("project_files")\
        .select("*")\
        .eq("project_id", project_id)\
        .order("created_at", desc=False)\
        .execute()

    return result.data


@router.get("/users/{user_id}/projects")
async def get_user_projects(user_id: str):
    result = supabase.table("projects")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True)\
        .execute()
    
    return result.data


@router.get("/users/{user_id}/projects/stats")
async def get_project_stats(user_id: str):
    result = supabase.table("projects")\
        .select("status")\
        .eq("user_id", user_id)\
        .execute()
    
    stats = {
        "consulting": 0,
        "writing": 0,
        "waiting": 0,
        "completed": 0
    }
    
    status_map = {1: "consulting", 2: "writing", 3: "waiting", 4: "completed"}
    
    for p in result.data:
        key = status_map.get(p["status"])
        if key:
            stats[key] += 1
    
    stats["total"] = len(result.data)
    
    return stats


@router.patch("/projects/{project_id}/draft")
async def save_draft(project_id: str, draft: DraftSave):
    project = supabase.table("projects")\
        .select("draft_data")\
        .eq("id", project_id)\
        .execute()
    
    if not project.data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    draft_data = project.data[0]["draft_data"] or {}
    draft_data[draft.step] = draft.data
    
    supabase.table("projects")\
        .update({
            "draft_data": draft_data,
            "updated_at": datetime.now().isoformat()
        })\
        .eq("id", project_id)\
        .execute()
    
    return {
        "success": True,
        "saved_at": datetime.now().isoformat()
    }


@router.patch("/projects/{project_id}/next-step")
async def next_step(project_id: str, draft: Optional[DraftSave] = None):
    project = supabase.table("projects")\
        .select("current_step, status, draft_data")\
        .eq("id", project_id)\
        .execute()
    
    if not project.data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    current_step = project.data[0]["current_step"]
    status = project.data[0]["status"]
    draft_data = project.data[0]["draft_data"] or {}
    
    if draft:
        draft_data[draft.step] = draft.data
    
    if current_step < 4:
        new_step = current_step + 1
        new_status = status
    else:
        new_step = current_step
        new_status = 3
    
    result = supabase.table("projects")\
        .update({
            "current_step": new_step,
            "status": new_status,
            "draft_data": draft_data,
            "updated_at": datetime.now().isoformat()
        })\
        .eq("id", project_id)\
        .execute()
    
    return result.data[0]


@router.patch("/projects/{project_id}/track")
async def select_track(project_id: str, track: TrackSelect):
    result = supabase.table("projects")\
        .update({
            "track": track.track,
            "updated_at": datetime.now().isoformat()
        })\
        .eq("id", project_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return result.data[0]


@router.patch("/projects/{project_id}/quick-check-result")
async def update_quick_check_result(project_id: str, qc: QuickCheckResult):
    update_data = {
        "quick_check_result": qc.result,
        "updated_at": datetime.now().isoformat()
    }
    
    if qc.result == "no_regulation":
        update_data["status"] = 4
    elif qc.result == "need_permit":
        update_data["status"] = 2
        update_data["current_step"] = 4
    
    result = supabase.table("projects")\
        .update(update_data)\
        .eq("id", project_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return result.data[0]


@router.patch("/projects/{project_id}/status")
async def update_project_status(project_id: str, status_update: ProjectStatusUpdate):
    update_data = {
        "status": status_update.status,
        "updated_at": datetime.now().isoformat()
    }
    
    if status_update.current_step:
        update_data["current_step"] = status_update.current_step
    
    result = supabase.table("projects")\
        .update(update_data)\
        .eq("id", project_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return result.data[0]