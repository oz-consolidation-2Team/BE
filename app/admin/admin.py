from fastapi import FastAPI
from sqladmin import Admin, ModelView

from app.admin.auth import AdminAuth
from app.core.config import SECRET_KEY
from app.core.db import engine
from app.models.admin_users import AdminUser
from app.models.company_info import CompanyInfo
from app.models.company_users import CompanyUser
from app.models.favorites import Favorite
from app.models.interests import Interest
from app.models.job_applications import JobApplication
from app.models.job_postings import JobPosting
from app.models.resumes import Resume
from app.models.resumes_educations import ResumeEducation
from app.models.users import User
from app.models.users_interests import UserInterest


class UserAdmin(ModelView, model=User):
    column_list = User.__table__.columns.keys()
    name = "회원"
    name_plural = "회원 목록"
    column_labels = {
        "id": "번호",
        "name": "이름",
        "email": "이메일",
        "user_image": "이미지",
        "password": "비밀번호",
        "phone_number": "전화번호",
        "birthday": "생년월일",
        "gender": "성별",
        "signup_purpose": "가입 목적",
        "referral_source": "유입경로",
        "is_active": "이메일 활성상태",
        "created_at": "가입일",
        "updated_at": "수정일",
        "resumes": "이력서",
        "applications": "지원 내역",
        "favorites": "즐겨찾기",
    }


class JobPostingAdmin(ModelView, model=JobPosting):
    column_list = JobPosting.__table__.columns.keys()
    name = "공고"
    name_plural = "공고 목록"
    column_labels = {
        "id": "번호",
        "title": "제목",
        "author_id": "담당자",
        "company_id": "회사",
        "recruit_period_start": "모집 시작일",
        "recruit_period_end": "모집 종료일",
        "is_always_recruiting": "상시 모집 여부",
        "education": "요구 학력",
        "recruit_number": "모집 인원",
        "benefits": "복리 후생",
        "preferred_conditions": "우대 조건",
        "other_conditions": "기타 조건",
        "work_address": "근무지",
        "work_place_name": "근무지명",
        "payment_method": "급여 지급 방법",
        "job_category": "직종",
        "work_duration": "근무 기간",
        "career": "경력",
        "employment_type": "고용형태",
        "salary": "급여",
        "deadline_at": "마감일",
        "work_days": "근무요일/스케줄",
        "description": "공고상세내용",
        "posings_image": "공고이미지",
        "created_at": "작성일",
        "updated_at": "수정일",
        "author": "작성자",
        "company": "회사",
        "favorites": "즐겨찾기",
        "applications": "지원 내역",
    }


class FavoriteAdmin(ModelView, model=Favorite):
    column_list = Favorite.__table__.columns.keys()
    name = "즐겨찾기"
    name_plural = "즐겨찾기 목록"
    column_labels = {
        "id": "번호",
        "user_id": "회원",
        "job_posting_id": "공고",
        "created_at": "작성일",
        "user": "회원",
        "job_posting": "공고",
    }


class AdminUserAdmin(ModelView, model=AdminUser):
    column_list = AdminUser.__table__.columns.keys()
    name = "관리자"
    name_plural = "관리자 목록"
    column_labels = {"id": "번호", "username": "아이디", "password": "비밀번호"}


class CompanyInfoAdmin(ModelView, model=CompanyInfo):
    column_list = CompanyInfo.__table__.columns.keys()
    name = "기업 정보"
    name_plural = "기업 정보 목록"
    column_labels = {
        "id": "번호",
        "company_name": "기업명",
        "business_reg_number": "사업자등록번호",
        "opening_date": "개업일",
        "company_intro": "기업 소개",
        "ceo_name": "대표자 성함",
        "address": "사업장 주소",
        "company_image": "회사 이미지 URL",
        "job_postings": "작성한 공고",
        "company_users": "담당자",
    }


class CompanyUserAdmin(ModelView, model=CompanyUser):
    column_list = CompanyUser.__table__.columns.keys()
    name = "기업 담당자"
    name_plural = "기업 담당자 목록"
    column_labels = {
        "id": "번호",
        "company_id": "기업 번호",
        "password": "비밀번호",
        "manager_name": "담당자 이름",
        "manager_phone": "담당자 전화번호",
        "manager_email": "담당자 이메일",
        "created_at": "가입일",
        "updated_at": "수정일",
        "email": "로그인 이메일",
        "company": "소속 회사",
        "job_postings": "작성한 공고",
    }


class jobApplicationAdmin(ModelView, model=JobApplication):
    column_list = JobApplication.__table__.columns.keys()
    name = "지원 내역"
    name_plural = "지원 내역 목록"
    column_labels = {
        "id": "번호",
        "user_id": "회원",
        "job_posting_id": "공고",
        "status": "상태",
        "created_at": "작성일",
        "updated_at": "수정일",
        "user": "회원",
        "job_posting": "공고",
    }


class ResumeAdmin(ModelView, model=Resume):
    column_list = Resume.__table__.columns.keys()
    name = "이력서"
    name_plural = "이력서 목록"
    column_labels = {
        "id": "번호",
        "user_id": "회원",
        "resume_image": "이미지",
        "company_name": "이전회사명",
        "position": "직급/직무",
        "work_period_start": "근무 시작일",
        "work_period_end": "근무 종료일",
        "desired_area": "희망 지역",
        "introduction": "자기소개",
        "created_at": "작성일",
        "updated_at": "수정일",
        "user": "회원",
        "educations": "학력",
    }


class ResumeEducationAdmin(ModelView, model=ResumeEducation):
    column_list = ResumeEducation.__table__.columns.keys()
    name = "학력"
    name_plural = "학력 목록"
    column_labels = {
        "id": "번호",
        "resumes_id": "이력서",
        "education_type": "학력구분",
        "school_name": "학교명",
        "education_status": "학력상태",
        "major": "전공",
        "degree": "학위",
        "start_date": "시작일",
        "end_date": "종료일",
        "resume": "이력서",
        "created_at": "작성일",
        "updated_at": "수정일",
    }


class InterestAdmin(ModelView, model=Interest):
    column_list = Interest.__table__.columns.keys()
    name = "관심분야"
    name_plural = "관심분야 목록"
    column_labels = {
        "id": "번호",
        "code": "코드",
        "name": "이름",
        "is_custom": "사용자 정의 항목 여부",
        "user_interests": "회원 관심분야",
    }


class UserInterestAdmin(ModelView, model=UserInterest):
    column_list = UserInterest.__table__.columns.keys()
    name = "회원 관심분야"
    name_plural = "회원 관심분야 목록"
    column_labels = {
        "id": "번호",
        "user_id": "회원",
        "interest_id": "관심분야",
        "user": "회원",
        "interest": "관심분야",
    }


def setup_admin(app: FastAPI):
    admin = Admin(
        app,
        engine,
        base_url="/admin",
        authentication_backend=AdminAuth(secret_key=SECRET_KEY),
    )
    admin.add_view(AdminUserAdmin)
    admin.add_view(UserAdmin)
    admin.add_view(UserInterestAdmin)
    admin.add_view(InterestAdmin)
    admin.add_view(JobPostingAdmin)
    admin.add_view(FavoriteAdmin)
    admin.add_view(CompanyInfoAdmin)
    admin.add_view(CompanyUserAdmin)
    admin.add_view(jobApplicationAdmin)
    admin.add_view(ResumeAdmin)
    admin.add_view(ResumeEducationAdmin)
