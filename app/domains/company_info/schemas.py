from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict

from app.domains.company_users.schemas import JobPostingsSummary


class PublicCompanyInfo(BaseModel):
    company_id: int
    company_name: str
    company_intro: str
    business_reg_number: str
    opening_date: str  # YYYY-MM-DD 문자열
    ceo_name: str
    manager_name: str
    manager_email: str
    manager_phone: str
    address: Optional[str]  # 선택 필드
    company_image: Optional[str]  # 선택 필드
    job_postings: List[JobPostingsSummary] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
