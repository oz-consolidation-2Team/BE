from typing import Any
from enum import Enum

from fastapi import APIRouter, Depends, Query, status, UploadFile, File
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.utils import get_current_company_user
from app.domains.job_postings import service
from app.domains.job_postings.schemas import (
                                                JobPostingResponse,
                                                JobPostingUpdate,
                                                PaginatedJobPostingResponse,
                                                JobPostingCreateFormData) # 스키마 임포트
from app.models.company_users import CompanyUser
from app.models.job_postings import JobPosting, JobCategoryEnum # 모델 임포트

# 정렬 옵션 정의 Enum
class SortOptions(str, Enum):
    LATEST = "latest"
    DEADLINE = "deadline"
    SALARY_HIGH = "salary_high"
    SALARY_LOW = "salary_low"

# API 라우터 설정 (prefix, tags 지정)
router = APIRouter(prefix="/posting", tags=["채용공고"])


# --- Helper Functions (라우터 내부용) ---

async def get_posting_or_404(
    session: AsyncSession, job_posting_id: int
) -> JobPosting:
    """ID로 채용공고를 조회하고 없으면 404 에러 발생시키는 헬퍼 함수"""
    # 서비스 계층 함수 호출
    posting = await service.get_job_posting(session, job_posting_id)
    # 결과 없으면 404 예외 발생
    if not posting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="채용공고를 찾을 수 없습니다.")
    return posting


async def check_posting_permission(
    posting: JobPosting, current_user: CompanyUser, action_type: str = "접근"
):
    """채용공고에 대한 현재 사용자의 권한(소유권) 확인 헬퍼 함수"""
    # 작성자와 현재 사용자가 다르면 403 예외 발생
    if posting.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"본인 공고만 {action_type}할 수 있습니다.")


# --- API Endpoints ---

@router.post(
    "/",
    response_model=JobPostingResponse, # 응답 형식 지정
    status_code=status.HTTP_201_CREATED, # 성공 상태 코드
    summary="채용공고 생성",
    description="로그인된 기업 담당자가 새로운 채용공고를 등록합니다. 이미지 파일을 함께 업로드할 수 있습니다.",
)
async def create_job_posting(
    # 의존성 주입: Form 데이터, 이미지 파일, DB 세션, 현재 사용자 정보
    form_data: JobPostingCreateFormData = Depends(), # Form 데이터 처리 클래스
    image_file: UploadFile = File(None, description="채용공고 이미지 파일 (선택사항)"),
    session: AsyncSession = Depends(get_db_session),
    current_user: CompanyUser = Depends(get_current_company_user),
) -> JobPosting: # 성공 시 JobPosting ORM 객체 반환 (response_model에 의해 변환됨)
    """채용공고 생성 API 엔드포인트"""
    try:
        # 1. Form 데이터를 JobPostingCreate Pydantic 모델로 변환/검증 (스키마 클래스 내 메서드 사용)
        job_posting_create_data = form_data.parse_to_job_posting_create(postings_image_url=None)

        # 2. 서비스 계층 함수 호출하여 공고 생성 로직 수행
        created_posting = await service.create_job_posting(
            session=session,
            job_posting_data=job_posting_create_data, # 검증된 데이터 전달
            author_id=current_user.id,
            company_id=current_user.company_id,
            image_file=image_file, # 이미지 파일 전달
        )
        # 3. 생성된 공고 객체 반환
        return created_posting
    except HTTPException as http_exc:
        # 스키마 변환/검증 또는 서비스 로직에서 발생한 HTTP 예외는 그대로 전달
        raise http_exc
    except Exception as e:
        # 그 외 예상치 못한 서버 오류 처리 (로그 출력 + 500 에러 반환)
        print(f"Error: 채용 공고 생성 라우터 오류 - {e}") # 실제 운영에서는 logger 사용 권장
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"채용 공고 생성 중 서버 오류 발생: {e}"
        )


@router.get(
    "/",
    response_model=PaginatedJobPostingResponse, # 페이지네이션 응답 형식
    summary="채용공고 목록 조회",
    description="채용공고 목록을 페이지네이션하여 조회합니다.",
)
async def list_postings(
    # 의존성 주입: 쿼리 파라미터 (skip, limit), DB 세션
    skip: int = Query(0, ge=0, description="건너뛸 레코드 수"),
    limit: int = Query(10, ge=1, le=100, description="가져올 레코드 수"),
    session: AsyncSession = Depends(get_db_session)
) -> PaginatedJobPostingResponse:
    """채용공고 목록 조회 API 엔드포인트"""
    # 서비스 계층 호출 (목록 및 전체 개수 가져오기)
    postings, total_count = await service.list_job_postings(
        session=session, skip=skip, limit=limit
    )

    # 페이지네이션 응답 객체 생성 및 반환
    return PaginatedJobPostingResponse(
        items=postings,
        total=total_count,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/search",
    response_model=PaginatedJobPostingResponse, # 페이지네이션 응답 형식
    summary="채용공고 검색",
    description="키워드 및 필터 기반으로 채용공고를 검색합니다.",
)
async def search_postings(
    # 의존성 주입: 검색 관련 쿼리 파라미터들, DB 세션
    keyword: str | None = Query(None, description="검색 키워드 (제목, 내용에서 검색)"),
    location: str | None = Query(None, description="근무지 위치"),
    job_category: JobCategoryEnum | None = Query(None, description="직무 카테고리"),
    employment_type: str | None = Query(None, description="고용 형태"),
    is_always_recruiting: bool | None = Query(None, description="상시 채용 여부"),
    page: int = Query(1, ge=1, description="페이지 번호"), # 페이지 번호로 받음
    limit: int = Query(10, ge=1, le=100, description="페이지당 결과 수"),
    sort: SortOptions = Query(SortOptions.LATEST, description="정렬 기준"),
    session: AsyncSession = Depends(get_db_session)
) -> PaginatedJobPostingResponse:
    """채용공고 검색 API 엔드포인트"""
    # 서비스 계층 호출 (검색 로직 수행)
    postings, total_count = await service.search_job_postings(
        session=session,
        keyword=keyword,
        location=location,
        job_category=job_category.value if job_category else None, # Enum은 value 전달
        employment_type=employment_type,
        is_always_recruiting=is_always_recruiting,
        page=page, # page 번호 전달
        limit=limit,
        sort=sort.value # Enum은 value 전달
    )

    # 페이지네이션 응답 객체 생성 및 반환 (page -> skip 계산)
    return PaginatedJobPostingResponse(
        items=postings,
        total=total_count,
        skip=(page - 1) * limit, # skip 값 계산
        limit=limit,
    )


@router.get(
    "/popular",
    response_model=PaginatedJobPostingResponse, # 페이지네이션 응답 형식
    summary="인기 채용공고 목록 조회",
    description="지원자 수가 많은 인기 채용공고를 조회합니다.",
)
async def list_popular_postings(
    # 의존성 주입: 쿼리 파라미터(limit), DB 세션
    limit: int = Query(10, ge=1, le=100, description="가져올 레코드 수"),
    session: AsyncSession = Depends(get_db_session)
) -> PaginatedJobPostingResponse:
    """인기 채용공고 목록 조회 API 엔드포인트"""
    # 서비스 계층 호출 (인기 공고 조회 로직)
    postings, total_count = await service.get_popular_job_postings(
        session=session, limit=limit
    )

    # 페이지네이션 응답 객체 생성 및 반환
    # 참고: 이 경우 total_count는 전체 공고 수를 의미하므로 API 스펙 정의 필요
    return PaginatedJobPostingResponse(
        items=postings,
        total=total_count, # 서비스에서 반환된 전체 공고 수
        skip=0, # 인기 목록은 skip 개념이 보통 없음
        limit=limit,
    )


@router.get(
    "/{job_posting_id}", # 경로 파라미터로 공고 ID 받음
    response_model=JobPostingResponse, # 단일 공고 응답 형식
    summary="채용공고 상세 조회",
    description="특정 채용공고의 상세정보를 조회합니다.",
)
async def get_posting(
    # 의존성 주입: 경로 파라미터, DB 세션
    job_posting_id: int, session: AsyncSession = Depends(get_db_session)
) -> JobPosting: # 성공 시 ORM 객체 반환
    """채용공고 상세 조회 API 엔드포인트"""
    # 헬퍼 함수 사용하여 공고 조회 (없으면 404 발생)
    posting = await get_posting_or_404(session, job_posting_id)
    # 조회된 공고 반환
    return posting


@router.patch(
    "/{job_posting_id}", # 경로 파라미터로 공고 ID 받음
    response_model=JobPostingResponse, # 성공 시 업데이트된 공고 정보 반환
    summary="채용공고 수정",
    description="로그인된 기업 담당자가 자신이 올린 채용공고를 수정합니다.",
)
async def update_posting(
    # 의존성 주입: 경로 파라미터, 요청 본문(수정 데이터), DB 세션, 현재 사용자
    job_posting_id: int,
    data: JobPostingUpdate, # 요청 본문은 JobPostingUpdate 스키마로 검증
    session: AsyncSession = Depends(get_db_session),
    current_user: CompanyUser = Depends(get_current_company_user),
) -> JobPosting: # 성공 시 ORM 객체 반환
    """채용공고 수정 API 엔드포인트"""
    # 1. 공고 조회 (없으면 404)
    posting = await get_posting_or_404(session, job_posting_id)

    # 2. 수정 권한 확인 (본인 공고인지)
    await check_posting_permission(posting, current_user, action_type="수정")

    # 3. 서비스 계층 호출 (업데이트 로직 수행)
    updated_posting = await service.update_job_posting(
        session=session, job_posting_id=job_posting_id, data=data
    )
    # 4. 서비스 결과 확인 (정상 처리 시 업데이트된 객체, 실패/못찾음 시 None 예상)
    if updated_posting is None:
        # 서비스에서 None 반환 시 (예: DB 오류 외 다른 이유로 실패) 500 에러 발생
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="공고 업데이트 처리 중 오류 발생")

    # 5. 업데이트된 공고 반환
    return updated_posting


@router.delete(
    "/{job_posting_id}", # 경로 파라미터로 공고 ID 받음
    status_code=status.HTTP_204_NO_CONTENT, # 성공 시 응답 본문 없음
    summary="채용공고 삭제",
    description="로그인된 기업 담당자가 자신이 올린 채용공고를 삭제합니다.",
)
async def delete_posting(
    # 의존성 주입: 경로 파라미터, DB 세션, 현재 사용자
    job_posting_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: CompanyUser = Depends(get_current_company_user),
) -> None: # 성공 시 반환값 없음
    """채용공고 삭제 API 엔드포인트"""
    # 1. 공고 조회 (없으면 404)
    posting = await get_posting_or_404(session, job_posting_id)

    # 2. 삭제 권한 확인 (본인 공고인지)
    await check_posting_permission(posting, current_user, action_type="삭제")

    # 3. 서비스 계층 호출 (삭제 로직 수행)
    # 서비스 함수는 내부에서 DB 에러 시 HTTPException 발생시킴
    await service.delete_job_posting(session=session, job_posting_id=job_posting_id)

    # 4. 서비스 호출이 성공적으로 완료되면 (예외 발생X), None 반환하여 204 응답 처리
    return None