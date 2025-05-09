from datetime import date

from pydantic import field_validator
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from app.core.datetime_utils import get_now_utc
from app.models.base import Base


class ResumeExperience(Base):                              # 경력사항 테이블 정의
    def __init__(self, **kw):
        super().__init__(**kw)

    __tablename__ = "resume_experiences"
    id = Column(Integer, primary_key=True, index=True)     # 기본키
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"))
    company_name = Column(String(100), nullable=False)     # 회사명
    position = Column(String(100), nullable=True)         # 직무/직급
    start_date = Column(Date, nullable=True)               # 근무 시작일
    end_date = Column(Date, nullable=True)                 # 근무 종료일
    description = Column(Text, nullable=True)              # 상세 업무 내용
    created_at = Column(DateTime(timezone=True), default=get_now_utc)    # 생성일
    updated_at = Column(DateTime(timezone=True), default=get_now_utc, onupdate=get_now_utc)  # 수정일

    resume = relationship("Resume", back_populates="experiences")

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_month_only(cls, value):
        # 예: '2023-06' → '2023-06-01'
        if value:
            return date.fromisoformat(f"{value}-01")
        return None

    def __str__(self):
        return f"{self.company_name} - {self.position}"