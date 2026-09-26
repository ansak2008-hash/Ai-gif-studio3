from __future__ import annotations
from datetime import UTC,datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID,uuid4
import hashlib
from sqlalchemy import select,update
from sqlalchemy.ext.asyncio import async_sessionmaker
from ai_gif_studio.models import JobStatus,ProcessingJob,ProcessingMode,VideoSubmission
from .tables import ProcessingJobRecord,ArtifactRecord
class JobRepository(Protocol):
    async def create(self,submission:VideoSubmission)->ProcessingJob: ...
    async def get(self,job_id:UUID)->ProcessingJob|None: ...
class SqlAlchemyJobRepository:
    def __init__(self,session_factory:async_sessionmaker): self._session_factory=session_factory
    async def create(self,submission):
        job=ProcessingJob(id=uuid4(),status=JobStatus.CREATED,submission=submission,created_at=datetime.now(UTC))
        record=ProcessingJobRecord(id=str(job.id),status=job.status.value,telegram_file_id=submission.telegram_file_id,original_filename=submission.original_filename,content_type=submission.content_type,file_size_bytes=submission.file_size_bytes,submitted_by=submission.submitted_by,mode=submission.mode.value,created_at=job.created_at)
        async with self._session_factory() as session: session.add(record); await session.commit()
        return job
    async def get(self,job_id:UUID):
        async with self._session_factory() as session: record=await session.scalar(select(ProcessingJobRecord).where(ProcessingJobRecord.id==str(job_id)))
        if record is None:return None
        return ProcessingJob(id=UUID(record.id),status=JobStatus(record.status),created_at=record.created_at,submission=VideoSubmission(record.telegram_file_id,record.original_filename,record.content_type,record.file_size_bytes,record.submitted_by,ProcessingMode(record.mode)))
    async def set_status(self,job_id:UUID,status:str):
        async with self._session_factory() as session:
            await session.execute(update(ProcessingJobRecord).where(ProcessingJobRecord.id==str(job_id)).values(status=status)); await session.commit()
class ArtifactRepository:
    def __init__(self,session_factory:async_sessionmaker): self._session_factory=session_factory
    async def register(self,job_id:UUID,path:Path,artifact_type:str,mime_type:str):
        h=hashlib.sha256(); size=0
        with path.open("rb") as f:
            for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk); size+=len(chunk)
        row=ArtifactRecord(artifact_id=str(uuid4()),job_id=str(job_id),type=artifact_type,storage_path=str(path),mime_type=mime_type,size_bytes=size,sha256=h.hexdigest(),created_at=datetime.now(UTC),metadata={})
        async with self._session_factory() as session: session.add(row); await session.commit()
        return row
