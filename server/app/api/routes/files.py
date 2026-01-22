from fastapi import APIRouter, HTTPException, UploadFile, File
from app.core.config import supabase

router = APIRouter()


@router.post("/projects/{project_id}/files")
async def upload_file(project_id: str, file: UploadFile = File(...)):
    project = supabase.table("projects")\
        .select("id")\
        .eq("id", project_id)\
        .execute()
    
    if not project.data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    file_content = await file.read()
    file_path = f"{project_id}/{file.filename}"
    
    supabase.storage\
        .from_("user-files")\
        .upload(file_path, file_content)
    
    file_type = file.filename.split(".")[-1] if "." in file.filename else ""
    
    result = supabase.table("files").insert({
        "project_id": project_id,
        "file_name": file.filename,
        "file_path": file_path,
        "file_type": file_type
    }).execute()
    
    return result.data[0]


@router.get("/projects/{project_id}/files")
async def get_project_files(project_id: str):
    result = supabase.table("files")\
        .select("*")\
        .eq("project_id", project_id)\
        .order("created_at", desc=True)\
        .execute()
    
    return result.data


@router.get("/files/{file_id}/download")
async def get_download_url(file_id: str):
    file_info = supabase.table("files")\
        .select("file_path, file_name")\
        .eq("id", file_id)\
        .execute()
    
    if not file_info.data:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = file_info.data[0]["file_path"]
    
    url = supabase.storage\
        .from_("user-files")\
        .get_public_url(file_path)
    
    return {
        "file_name": file_info.data[0]["file_name"],
        "download_url": url
    }


@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    file_info = supabase.table("files")\
        .select("file_path")\
        .eq("id", file_id)\
        .execute()
    
    if not file_info.data:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = file_info.data[0]["file_path"]
    
    supabase.storage\
        .from_("user-files")\
        .remove([file_path])
    
    supabase.table("files")\
        .delete()\
        .eq("id", file_id)\
        .execute()
    
    return {"success": True, "message": "File deleted"}