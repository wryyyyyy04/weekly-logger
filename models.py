from sqlalchemy import create_engine, Column, Integer, String, Text, Date, DateTime, func
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import date
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
engine = create_engine(f"sqlite:///{BASE_DIR}/data/weekly.db", echo=False)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class DailyTodo(Base):
    __tablename__ = "daily_todos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, default=date.today)
    content = Column(Text, nullable=False)
    category = Column(String(20), default="todo")  # todo / experiment
    status = Column(String(20), default="pending")  # pending / completed / cancelled
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ExperimentLog(Base):
    __tablename__ = "experiment_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, default=date.today)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    equipment = Column(String(200))
    results = Column(Text)
    tags = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class WeeklySection(Base):
    __tablename__ = "weekly_sections"
    id = Column(Integer, primary_key=True, autoincrement=True)
    week_start = Column(Date, nullable=False)
    section_type = Column(String(30), nullable=False)
    # plan / progress / pending / next_plan / assessment
    content = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Milestone(Base):
    __tablename__ = "milestones"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # report / paper / defense
    planned_date = Column(Date)
    actual_date = Column(Date)
    notes = Column(Text)
    sort_order = Column(Integer, default=0)


class FileAttachment(Base):
    __tablename__ = "file_attachments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(200), nullable=False)        # UUID储存名
    original_name = Column(String(300), nullable=False)    # 原始文件名
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)
    content_type = Column(String(100))
    todo_id = Column(Integer, nullable=True)              # 关联待办
    experiment_id = Column(Integer, nullable=True)        # 关联实验
    date = Column(Date, nullable=False, default=date.today)
    created_at = Column(DateTime, server_default=func.now())


def init_db():
    Base.metadata.create_all(bind=engine)
    # 初始化默认里程碑节点
    with SessionLocal() as db:
        if db.query(Milestone).count() == 0:
            defaults = [
                Milestone(name="选题报告定稿/综述发表日期", type="report",
                          notes="距正式申请答辩至少24个月", sort_order=1),
                Milestone(name="中期报告定稿/第一篇论文发表日期", type="paper",
                          notes="距正式申请答辩至少12个月", sort_order=2),
                Milestone(name="最终学术报告定稿/第二篇论文发表日期", type="paper",
                          notes="距正式申请答辩至少6个月", sort_order=3),
                Milestone(name="博士学位论文定稿", type="defense",
                          notes="距正式申请答辩至少3个月", sort_order=4),
            ]
            db.add_all(defaults)
            db.commit()
