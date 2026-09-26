from __future__ import annotations
from datetime import datetime
from uuid import uuid4
from sqlalchemy import DateTime,Integer,String,Text,JSON,ForeignKey
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column
class Base(DeclarativeBase): pass
class ProcessingJobRecord(Base):
    __tablename__="processing_jobs"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    status:Mapped[str]=mapped_column(String(32),nullable=False,index=True)
    telegram_file_id:Mapped[str]=mapped_column(String(255),nullable=False)
    original_filename:Mapped[str|None]=mapped_column(String(255))
    content_type:Mapped[str|None]=mapped_column(String(128))
    file_size_bytes:Mapped[int]=mapped_column(Integer,nullable=False)
    submitted_by:Mapped[int]=mapped_column(Integer,nullable=False,index=True)
    mode:Mapped[str]=mapped_column(String(32),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
class ArtifactRecord(Base):
    __tablename__="artifacts"
    artifact_id:Mapped[str]=mapped_column(String(36),primary_key=True)
    job_id:Mapped[str]=mapped_column(String(36),ForeignKey("processing_jobs.id"),index=True,nullable=False)
    type:Mapped[str]=mapped_column(String(64),nullable=False)
    storage_path:Mapped[str]=mapped_column(Text,nullable=False)
    mime_type:Mapped[str]=mapped_column(String(128),nullable=False)
    size_bytes:Mapped[int]=mapped_column(Integer,nullable=False)
    sha256:Mapped[str]=mapped_column(String(64),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    expires_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    metadata:Mapped[dict]=mapped_column(JSON,default=dict,nullable=False)
class JobStepRecord(Base):
    __tablename__="job_steps"
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    job_id:Mapped[str]=mapped_column(String(36),ForeignKey("processing_jobs.id"),index=True,nullable=False)
    name:Mapped[str]=mapped_column(String(128),nullable=False)
    status:Mapped[str]=mapped_column(String(32),nullable=False,index=True)
    started_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    completed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    duration_ms:Mapped[int|None]=mapped_column(Integer)
    retry_count:Mapped[int]=mapped_column(Integer,default=0,nullable=False)
    error:Mapped[str|None]=mapped_column(Text)
