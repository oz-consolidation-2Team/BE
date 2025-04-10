from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.job_postings import JobPosting
from app.domains.job_postings.schemas import JobPostingCreate

async def create_job_posting(
    session: AsyncSession,
    data: JobPostingCreate,
    author_id: int,
    company_id: int
) -> JobPosting:
    job_posting = JobPosting(
        **data.model_dump(),
        author_id=author_id,
        company_id=company_id
    )
    session.add(job_posting)
    await session.commit()
    await session.refresh(job_posting)
    return job_posting

async def list_job_postings(session: AsyncSession) -> list[JobPosting]:
    result = await session.execute(select(JobPosting).order_by(JobPosting.created_at.desc()))
    return result.scalars().all()

async def get_job_posting(session: AsyncSession, job_posting_id: int) -> JobPosting | None:
    result = await session.execute(
        select(JobPosting).where(JobPosting.id == job_posting_id)
    )
    return result.scalars().first()