from datetime import datetime, timedelta

import jwt
from fastapi import HTTPException, status, BackgroundTasks
from sqlalchemy import delete, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import ALGORITHM, SECRET_KEY
from app.core.utils import create_access_token
from app.domains.company_users.schemas import (
    CompanyTokenRefreshRequest,
    CompanyUserBase,
    CompanyUserRegisterRequest,
    CompanyUserUpdateRequest,
    FindCompanyUserEmail,
    JobPostingsSummary,
    PasswordResetVerifyRequest,
)
from app.domains.company_users.utiles import (
    check_password_match,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models import CompanyInfo, CompanyUser
from app.models.job_postings import JobPosting
from app.models.users import EmailVerification


# 사업자 등록번호 중복 확인
async def check_dupl_business_number(db: AsyncSession, business_reg_number: str):
    result = await db.execute(
        select(CompanyInfo).filter_by(business_reg_number=business_reg_number)
    )
    company_reg_no = result.scalars().first()
    if company_reg_no:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 사업자등록번호입니다.",
        )

# 기업 정보 저장
async def create_company_info(db: AsyncSession, payload: CompanyUserBase):
    company_info = CompanyInfo(
        company_name=payload.company_name,
        manager_name=payload.manager_name,
        manager_phone=payload.manager_phone,
        manager_email=str(payload.manager_email),
        ceo_name=payload.ceo_name,
        business_reg_number=payload.business_reg_number,
        opening_date=payload.opening_date,
        company_intro=payload.company_intro,
    )
    db.add(company_info)
    await db.flush()  # 임시 저장 (ID 생성을 위해)
    return company_info


# 기업 회원 저장
async def create_company_user(
    db: AsyncSession, payload: CompanyUserBase, company_id: int) -> CompanyUser:
    company_user = CompanyUser(
        email=str(payload.email),
        password=hash_password(payload.password),
        company_id=company_id,
    )
    company_user.is_active = True  # 이메일 인증을 통과한 경우 활성화 설정
    db.add(company_user)
    await db.commit()
    await db.refresh(company_user)
    return company_user


# 기업 회원 가입
async def register_company_user(db: AsyncSession, payload: CompanyUserRegisterRequest):
    # 이메일, 사업자 중복 확인
    await check_dupl_business_number(db, payload.business_reg_number)
    check_password_match(payload.password, payload.confirm_password)

    # 이메일 인증 여부 확인
    result = await db.execute(
        select(EmailVerification).where(
            EmailVerification.email == str(payload.email),
            EmailVerification.is_verified == True,
            EmailVerification.user_type == "company"
        )
    )
    verified = result.scalar_one_or_none()
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이메일 인증이 완료되지 않았습니다."
        )

    # 정보 저장
    try:
        company_info = await create_company_info(db, payload)  # 기업 정보 저장
        company_user = await create_company_user(db, payload, company_info.id) # 기업 유저 정보 저장
        return company_user
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 처리 중 오류가 발생했습니다.",
        )


# 기업 회원 로그인
async def login_company_user(db: AsyncSession, email: str, password: str):
    result = await db.execute(select(CompanyUser).filter_by(email=email))
    company_user = result.scalars().first()

    # 유효값 검증
    if not company_user:
        raise HTTPException(
            status_code=401,
            detail="이메일 또는 비밀번호가 일치하지 않습니다.")
    if not company_user.is_active:
        raise HTTPException(status_code=403, detail="이메일 인증이 필요합니다.")
    if not verify_password(password, company_user.password):
        raise HTTPException(
            status_code=401,
            detail="이메일 또는 비밀번호가 일치하지 않습니다.",
        )

    return company_user


# 기업 회원 마이페이지 조회
async def get_company_user_mypage(db: AsyncSession, current_user: CompanyUser):

    result = await db.execute(
        select(CompanyUser)
        .options(
            selectinload(CompanyUser.company), selectinload(CompanyUser.job_postings)
        )
        .where(CompanyUser.id == current_user.id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="기업 회원 정보를 찾을 수 없습니다.",
        )
    company = user.company
    data = {
        "company_user_id": user.id,
        "email": user.email,
        "company_name": company.company_name,
        "company_id": company.id,
        "manager_name": company.manager_name,
        "manager_email": company.manager_email,
        "manager_phone": company.manager_phone,
        "company_intro": company.company_intro,
        "business_reg_number": company.business_reg_number,
        "opening_date": company.opening_date,
        "ceo_name": company.ceo_name,
        "address": company.address,
        "company_image": company.company_image,
        "job_postings": [
            JobPostingsSummary.from_orm(jp).dict() for jp in user.job_postings
        ],
    }
    return data


# 기업 회원 정보 수정
async def update_company_user(
    db: AsyncSession, payload: CompanyUserUpdateRequest, current_user: CompanyUser
):
    has_changes = False

    # 비밀번호 수정
    if payload.password:
        check_password_match(payload.password, payload.confirm_password)
        if not verify_password(payload.password, current_user.password):
            current_user.password = hash_password(payload.password)
            has_changes = True

    company = current_user.company
    # 수정할 유저 필드
    user_fields = {
        "manager_name": payload.manager_name,
        "manager_phone": payload.manager_phone,
        "manager_email": payload.manager_email,
        "company_intro": payload.company_intro,
        "address": payload.address,
        "company_image": payload.company_image,
    }

    for field, new_value in user_fields.items():
        if new_value is not None and getattr(company, field) != new_value:
            setattr(company, field, new_value)
            has_changes = True

    # 커밋 처리
    if has_changes:
        await db.commit()
        await db.refresh(company)

    result = {
        "company_user_id": current_user.id,
        "email": current_user.email,
        "company_name": company.company_name,
        "manager_name": company.manager_name,
        "manager_email": company.manager_email,
        "manager_phone": company.manager_phone,
        "company_intro": company.company_intro,
        "address": company.address,
        "company_image": company.company_image,
    }
    return result


# 기업 회원 탈퇴
async def delete_company_user(db: AsyncSession, current_user: CompanyUser):
    company_info = current_user.company

    company_id_to_check = None
    if company_info:
        company_id_to_check = company_info.id

    # JobPosting 먼저 삭제
    await db.execute(
        delete(JobPosting).where(JobPosting.author_id == current_user.id)
    )
    if company_id_to_check:
        await db.execute(
            delete(JobPosting).where(JobPosting.company_id == company_id_to_check)
        )

    # 이메일 인증 정보 삭제 (user_type='company'만 해당)
    await db.execute(
        delete(EmailVerification).where(
            and_(
                EmailVerification.email == current_user.email,
                EmailVerification.user_type == "company"
            )
        )
    )

    await db.delete(current_user)
    if company_info:
        await db.delete(company_info)  # 기업 정보도 삭제
    await db.commit()

    deleted_company_user = {
        "company_user_id": current_user.id,
        "company_name": company_info.company_name if company_info else "N/A",
    }
    return deleted_company_user


# 기업 회원 이메일 찾기
async def find_company_user_email(db: AsyncSession, payload: FindCompanyUserEmail):
    result = await db.execute(
        select(CompanyUser)
        .join(CompanyInfo)
        .where(
            CompanyInfo.ceo_name == payload.ceo_name,
            CompanyInfo.opening_date == payload.opening_date,
            CompanyInfo.business_reg_number == payload.business_reg_number,
            CompanyUser.company_id == CompanyInfo.id,
        )
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="일치하는 기업 회원을 찾을 수 없습니다.",
        )
    return {"company_name": user.company.company_name, "email": user.email}


# 기업회원 비밀번호 재설정- 사용자 찾고 짧은 jwt 발급
async def generate_password_reset_token(
    db: AsyncSession, payload: PasswordResetVerifyRequest
) -> str:
    # 사업자번호·개업일·대표자·이메일이 일치하는지 확인
    q = (
        select(CompanyUser)
        .join(CompanyInfo)
        .where(
            CompanyInfo.business_reg_number == payload.business_reg_number,
            CompanyInfo.opening_date == payload.opening_date,
            CompanyInfo.ceo_name == payload.ceo_name,
            CompanyUser.email == str(payload.email),
            CompanyUser.company_id == CompanyInfo.id,
        )
    )
    result = await db.execute(q)
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="일치하는 기업 회원을 찾을 수 없습니다.",
        )

    # 30분 만료의 reset-token 생성
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode = {"sub": user.email, "scope": "reset", "exp": expire}

    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


# 토큰으로 디코딩 후 비번 재설정
async def reset_password_with_token(
    db: AsyncSession,
    reset_token: str,
    new_password: str,
    confirm_password: str,
):
    # 1) 토큰 파싱 & 검증
    try:
        payload = jwt.decode(reset_token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="재설정 토큰이 만료되었습니다.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 재설정 토큰입니다.",
        )
    if payload.get("scope") != "reset" or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="재설정 토큰 정보가 올바르지 않습니다.",
        )
    # 2)비밀번호 일치 확인
    check_password_match(new_password, confirm_password)
    # 3) 사용자 조회 및 비번 업데이트
    email = payload["sub"]
    result = await db.execute(select(CompanyUser).filter_by(email=email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 이메일의 사용자를 찾을 수 없습니다.",
        )
    user.password = hash_password(new_password)
    await db.commit()


# 리프레쉬 토큰으로 엑세스토큰 재발급
async def refresh_company_user_access_token(
    db: AsyncSession, token_data: CompanyTokenRefreshRequest
):
    payload = decode_refresh_token(token_data.refresh_token)
    email: str = payload.get("sub")

    result = await db.execute(select(CompanyUser).filter_by(email=email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 기업 회원을 찾을 수 없습니다.",
        )
    new_access_token = await create_access_token(data={"sub": user.email})

    return {"access_token": new_access_token}
