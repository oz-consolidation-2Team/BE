from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Column, DateTime, JSON
from sqlalchemy import Enum as SQLAEnum
from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base


class ApplicationStatusEnum(str, Enum):
    applied = "지원완료"
    passed = "서류통과"
    accepted = "합격"
    rejected = "불합격"


class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_posting_id = Column(Integer, ForeignKey("job_postings.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    resumes_data = Column(
        JSON,
        nullable=False,
        comment="지원 시점 이력서 데이터 스냅샷"
    )


    status = Column(
        SQLAEnum(ApplicationStatusEnum, name="application_status_enum"),
        default=ApplicationStatusEnum.applied,
    )

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # 관계
    user = relationship("User", back_populates="applications")
    job_posting = relationship("JobPosting", back_populates="applications")
    resume = relationship("Resume", back_populates="applications")

    # 유저는 같은 공고에 중복 지원 못하게
    __table_args__ = (
        UniqueConstraint("resume_id", "job_posting_id", name="uq_resume_jobposting"),
    )

    def __str__(self):
        return f"{self.id} - {self.created_at}"