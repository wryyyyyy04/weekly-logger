import os
from datetime import date, datetime, timedelta
from typing import Optional

import uuid
import shutil

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func

from models import init_db, SessionLocal, DailyTodo, ExperimentLog, WeeklySection, Milestone, FileAttachment

app = FastAPI(title="实验日志与周报管理")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ── Pydantic schemas ──────────────────────────────────────────────

class TodoCreate(BaseModel):
    date: str
    content: str
    category: str = "todo"
    status: str = "pending"


class TodoUpdate(BaseModel):
    content: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None


class ExperimentCreate(BaseModel):
    date: str
    title: str
    description: Optional[str] = ""
    equipment: Optional[str] = ""
    results: Optional[str] = ""
    tags: Optional[str] = ""


class ExperimentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    equipment: Optional[str] = None
    results: Optional[str] = None
    tags: Optional[str] = None


class SectionWrite(BaseModel):
    week_start: str
    section_type: str
    content: str


class MilestoneWrite(BaseModel):
    name: str
    type: str
    planned_date: Optional[str] = None
    actual_date: Optional[str] = None
    notes: Optional[str] = ""
    sort_order: int = 0


# ── 依赖 ──────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Todo APIs ─────────────────────────────────────────────────────

@app.get("/api/todos")
def list_todos(date_from: Optional[str] = None, date_to: Optional[str] = None,
               category: Optional[str] = None, status: Optional[str] = None):
    with SessionLocal() as db:
        q = db.query(DailyTodo)
        if date_from:
            q = q.filter(DailyTodo.date >= datetime.strptime(date_from, "%Y-%m-%d").date())
        if date_to:
            q = q.filter(DailyTodo.date <= datetime.strptime(date_to, "%Y-%m-%d").date())
        if category:
            q = q.filter(DailyTodo.category == category)
        if status:
            q = q.filter(DailyTodo.status == status)
        rows = q.order_by(DailyTodo.date.desc(), DailyTodo.created_at.desc()).all()
        return [_serialize(r) for r in rows]


@app.post("/api/todos")
def create_todo(data: TodoCreate):
    with SessionLocal() as db:
        t = DailyTodo(
            date=datetime.strptime(data.date, "%Y-%m-%d").date(),
            content=data.content,
            category=data.category,
            status=data.status,
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        return _serialize(t)


@app.put("/api/todos/{tid}")
def update_todo(tid: int, data: TodoUpdate):
    with SessionLocal() as db:
        t = db.query(DailyTodo).filter(DailyTodo.id == tid).first()
        if not t:
            raise HTTPException(404, "未找到该记录")
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(t, k, v)
        db.commit()
        return {"ok": True}


@app.delete("/api/todos/{tid}")
def delete_todo(tid: int):
    with SessionLocal() as db:
        t = db.query(DailyTodo).filter(DailyTodo.id == tid).first()
        if not t:
            raise HTTPException(404, "未找到该记录")
        db.delete(t)
        db.commit()
        return {"ok": True}


# ── Experiment Log APIs ───────────────────────────────────────────

@app.get("/api/experiments")
def list_experiments(date_from: Optional[str] = None, date_to: Optional[str] = None):
    with SessionLocal() as db:
        q = db.query(ExperimentLog)
        if date_from:
            q = q.filter(ExperimentLog.date >= datetime.strptime(date_from, "%Y-%m-%d").date())
        if date_to:
            q = q.filter(ExperimentLog.date <= datetime.strptime(date_to, "%Y-%m-%d").date())
        rows = q.order_by(ExperimentLog.date.desc()).all()
        return [_serialize(r) for r in rows]


@app.post("/api/experiments")
def create_experiment(data: ExperimentCreate):
    with SessionLocal() as db:
        e = ExperimentLog(
            date=datetime.strptime(data.date, "%Y-%m-%d").date(),
            title=data.title,
            description=data.description,
            equipment=data.equipment,
            results=data.results,
            tags=data.tags,
        )
        db.add(e)
        db.commit()
        db.refresh(e)
        return _serialize(e)


@app.put("/api/experiments/{eid}")
def update_experiment(eid: int, data: ExperimentUpdate):
    with SessionLocal() as db:
        e = db.query(ExperimentLog).filter(ExperimentLog.id == eid).first()
        if not e:
            raise HTTPException(404, "未找到该记录")
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(e, k, v)
        db.commit()
        return {"ok": True}


@app.delete("/api/experiments/{eid}")
def delete_experiment(eid: int):
    with SessionLocal() as db:
        e = db.query(ExperimentLog).filter(ExperimentLog.id == eid).first()
        if not e:
            raise HTTPException(404, "未找到该记录")
        # 同时删除关联文件
        for f in db.query(FileAttachment).filter(FileAttachment.experiment_id == eid).all():
            _remove_file(f)
            db.delete(f)
        db.delete(e)
        db.commit()
        return {"ok": True}


# ── File Upload APIs ────────────────────────────────────────────────

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/api/files")
def list_files(date_from: Optional[str] = None, date_to: Optional[str] = None,
               todo_id: Optional[int] = None, experiment_id: Optional[int] = None):
    with SessionLocal() as db:
        q = db.query(FileAttachment)
        if date_from:
            q = q.filter(FileAttachment.date >= datetime.strptime(date_from, "%Y-%m-%d").date())
        if date_to:
            q = q.filter(FileAttachment.date <= datetime.strptime(date_to, "%Y-%m-%d").date())
        if todo_id:
            q = q.filter(FileAttachment.todo_id == todo_id)
        if experiment_id:
            q = q.filter(FileAttachment.experiment_id == experiment_id)
        rows = q.order_by(FileAttachment.date.desc(), FileAttachment.created_at.desc()).all()
        return [_serialize(r) for r in rows]


@app.post("/api/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    date: str = Form(""),
    todo_id: Optional[int] = Form(None),
    experiment_id: Optional[int] = Form(None),
):
    ext = os.path.splitext(file.filename or "unnamed")[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(file_path)
    upload_date = datetime.strptime(date, "%Y-%m-%d").date() if date else date.today()

    with SessionLocal() as db:
        fa = FileAttachment(
            filename=stored_name,
            original_name=file.filename or "unnamed",
            file_path=file_path,
            file_size=file_size,
            content_type=file.content_type,
            todo_id=todo_id,
            experiment_id=experiment_id,
            date=upload_date,
        )
        db.add(fa)
        db.commit()
        db.refresh(fa)
        return _serialize(fa)


@app.get("/api/files/{fid}/download")
def download_file(fid: int):
    with SessionLocal() as db:
        fa = db.query(FileAttachment).filter(FileAttachment.id == fid).first()
        if not fa or not os.path.exists(fa.file_path):
            raise HTTPException(404, "文件未找到")
        return FileResponse(
            fa.file_path,
            media_type=fa.content_type or "application/octet-stream",
            filename=fa.original_name,
        )


@app.delete("/api/files/{fid}")
def delete_file(fid: int):
    with SessionLocal() as db:
        fa = db.query(FileAttachment).filter(FileAttachment.id == fid).first()
        if not fa:
            raise HTTPException(404, "未找到该文件")
        _remove_file(fa)
        db.delete(fa)
        db.commit()
        return {"ok": True}


def _remove_file(fa):
    if fa.file_path and os.path.exists(fa.file_path):
        try:
            os.remove(fa.file_path)
        except OSError:
            pass


# ── Weekly Section APIs ───────────────────────────────────────────

@app.get("/api/sections")
def list_sections(week_start: str, section_type: Optional[str] = None):
    with SessionLocal() as db:
        ws_date = datetime.strptime(week_start, "%Y-%m-%d").date()
        q = db.query(WeeklySection).filter(WeeklySection.week_start == ws_date)
        if section_type:
            q = q.filter(WeeklySection.section_type == section_type)
        return [_serialize(r) for r in q.all()]


@app.post("/api/sections")
def save_section(data: SectionWrite):
    with SessionLocal() as db:
        ws_date = datetime.strptime(data.week_start, "%Y-%m-%d").date()
        existing = db.query(WeeklySection).filter(
            WeeklySection.week_start == ws_date,
            WeeklySection.section_type == data.section_type,
        ).first()
        if existing:
            existing.content = data.content
        else:
            s = WeeklySection(
                week_start=ws_date,
                section_type=data.section_type,
                content=data.content,
            )
            db.add(s)
        db.commit()
        return {"ok": True}


# ── Milestone APIs ────────────────────────────────────────────────

@app.get("/api/milestones")
def list_milestones():
    with SessionLocal() as db:
        return [_serialize(r) for r in db.query(Milestone).order_by(Milestone.sort_order).all()]


@app.put("/api/milestones/{mid}")
def update_milestone(mid: int, data: MilestoneWrite):
    with SessionLocal() as db:
        m = db.query(Milestone).filter(Milestone.id == mid).first()
        if not m:
            raise HTTPException(404, "未找到该里程碑")
        m.name = data.name
        m.type = data.type
        m.planned_date = datetime.strptime(data.planned_date, "%Y-%m-%d").date() if data.planned_date else None
        m.actual_date = datetime.strptime(data.actual_date, "%Y-%m-%d").date() if data.actual_date else None
        m.notes = data.notes
        m.sort_order = data.sort_order
        db.commit()
        return {"ok": True}


# ── Report Generation ─────────────────────────────────────────────

class ReportRequest(BaseModel):
    week_start: str


@app.post("/api/generate-report")
def generate_report(req: ReportRequest):
    from report_generator import generate_weekly_report
    ws_date = datetime.strptime(req.week_start, "%Y-%m-%d").date()
    pptx_path, pdf_path = generate_weekly_report(ws_date)
    return {"pptx": pptx_path, "pdf": pdf_path}


# ── Week summary (for the overview tab) ───────────────────────────

@app.get("/api/week-summary")
def week_summary(week_start: str):
    """返回指定周的数据汇总，前端用于填充周报面板"""
    ws_date = datetime.strptime(week_start, "%Y-%m-%d").date()
    week_end = ws_date + timedelta(days=6)

    with SessionLocal() as db:
        todos = db.query(DailyTodo).filter(
            DailyTodo.date >= ws_date, DailyTodo.date <= week_end
        ).order_by(DailyTodo.date.desc()).all()

        experiments = db.query(ExperimentLog).filter(
            ExperimentLog.date >= ws_date, ExperimentLog.date <= week_end
        ).order_by(ExperimentLog.date.desc()).all()

        sections = db.query(WeeklySection).filter(
            WeeklySection.week_start == ws_date
        ).all()

        milestones = db.query(Milestone).order_by(Milestone.sort_order).all()

        return {
            "todos": [_serialize(r) for r in todos],
            "experiments": [_serialize(r) for r in experiments],
            "sections": {s.section_type: s.content for s in sections},
            "milestones": [_serialize(r) for r in milestones],
        }


# ── Helper ────────────────────────────────────────────────────────

def _serialize(obj):
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    for k, v in d.items():
        if isinstance(v, (date, datetime)):
            d[k] = v.isoformat()
    return d


# ── Mount static files & serve index ──────────────────────────────

app.mount("/output", StaticFiles(directory=os.path.join(BASE_DIR, "output")), name="output")


@app.get("/")
def index():
    return FileResponse(os.path.join(BASE_DIR, "templates", "index.html"))


# ── Startup ───────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
