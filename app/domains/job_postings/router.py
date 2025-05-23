from typing import Optional
import logging

from fastapi import APIRouter, Depends, Query, status, UploadFile, File
from fastapi.exceptions import HTTPException

from app.core.utils import get_current_company_user, get_current_user_optional, upload_image_to_ncp
from app.domains.job_postings import service
from app.domains.job_postings.schemas import (
                                                JobPostingResponse,
                                                JobPostingUpdate,
                                                PaginatedJobPostingResponse,
                                                JobPostingCreateFormData,
                                                JobPostingCreate,
                                                JobPostingUpdateFormData,
                                                _parse_date, _parse_int, _parse_enum, _parse_float, _parse_bool,
                                                EducationEnum, PaymentMethodEnum, JobCategoryEnum, WorkDurationEnum,
                                                SortOptions
                                                )
from pydantic import ValidationError

from app.domains.job_postings.repository import JobPostingRepository
from app.domains.job_postings.service import get_job_posting_repository

from app.models.company_users import CompanyUser
from app.models.job_postings import JobPosting
from app.models.users import User

# 로거 설정
logger = logging.getLogger(__name__)

# 채용 공고 API 라우터
router = APIRouter(prefix="/posting", tags=["채용공고"])


# --- 라우터 내부 헬퍼 함수 ---

async def get_posting_or_404(
    job_posting_id: int,
    user_id: int | None = None,
    repository: JobPostingRepository = Depends(get_job_posting_repository)
) -> JobPosting:
    """ID로 채용공고 조회 후 없으면 404 에러 발생"""
    # 1. 서비스 호출하여 공고 조회 (로그인 시 즐겨찾기 포함)
    posting = await service.get_job_posting(
        job_posting_id=job_posting_id,
        repository=repository,
        user_id=user_id
    )
    # 2. 공고 존재 여부 확인 및 404 처리
    if not posting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="채용공고를 찾을 수 없습니다.")
    # 3. 조회된 공고 반환
    return posting


async def check_posting_permission(
    posting: JobPosting, current_user: CompanyUser, action_type: str = "접근"
):
    """채용공고에 대한 기업 사용자의 소유권 확인"""
    # 1. 공고 작성자와 현재 로그인한 기업 사용자가 동일한지 확인
    if posting.author_id != current_user.id:
        # 2. 동일하지 않으면 403 Forbidden 에러 발생
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"본인 공고만 {action_type}할 수 있습니다.")
    # 3. 동일하면 통과 (None 반환)


# --- API 엔드포인트 --- (HTTP 요청 처리)

@router.post(
    "/",
    response_model=JobPostingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="채용공고 생성",
    description="로그인된 기업 담당자가 새로운 채용공고를 등록합니다. 이미지 파일을 함께 업로드할 수 있습니다.",
)
async def create_job_posting(
    form_data: JobPostingCreateFormData = Depends(), # Form 데이터 수신
    postings_image: UploadFile = File(None, description="채용공고 이미지 파일 (선택사항)"),
    current_user: CompanyUser = Depends(get_current_company_user), # 현재 로그인한 기업 사용자
    repository: JobPostingRepository = Depends(get_job_posting_repository) # 서비스 호출 시 필요
) -> JobPosting:
    """채용공고 생성 API"""
    logger.info("POST /posting 요청 수신")
    # 1. 이미지 업로드 (선택적)
    postings_image_url = None
    if postings_image:
        try:
            # NCP Object Storage에 이미지 업로드 시도
            postings_image_url = await upload_image_to_ncp(postings_image, folder="job_postings")
        except Exception as e:
            # 이미지 업로드 실패 시 500 에러
            logger.exception("Error uploading image") # 예외 정보와 함께 에러 로그 기록
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"이미지 업로드 중 오류 발생: {e}")

    # 2. Form 데이터 파싱 및 Pydantic 모델 검증
    try:
        # Form 데이터를 딕셔너리로 변환 (스키마의 헬퍼 함수로 타입 변환 및 기본 검증)
        parsed_data = {
            "title": form_data.title,
            "recruit_period_start": _parse_date(form_data.recruit_period_start, "모집 시작일"),
            "recruit_period_end": _parse_date(form_data.recruit_period_end, "모집 종료일"),
            "is_always_recruiting": _parse_bool(form_data.is_always_recruiting_str, "상시 모집 여부"),
            "education": _parse_enum(EducationEnum, form_data.education, "요구 학력"),
            "recruit_number": _parse_int(form_data.recruit_number, "모집 인원", min_value=0),
            "benefits": form_data.benefits,
            "preferred_conditions": form_data.preferred_conditions,
            "other_conditions": form_data.other_conditions,
            "work_address": form_data.work_address,
            "work_place_name": form_data.work_place_name,
            "region1": form_data.region1,
            "region2": form_data.region2,
            "payment_method": _parse_enum(PaymentMethodEnum, form_data.payment_method, "급여 지급 방식"),
            "job_category": _parse_enum(JobCategoryEnum, form_data.job_category, "직종 카테고리"),
            "work_duration": _parse_enum(WorkDurationEnum, form_data.work_duration, "근무 기간"),
            "is_work_duration_negotiable": _parse_bool(form_data.is_work_duration_negotiable_str, "근무 기간 협의 가능 여부"),
            "career": form_data.career,
            "employment_type": form_data.employment_type,
            "salary": _parse_int(form_data.salary, "급여", min_value=0),
            "work_days": form_data.work_days,
            "is_work_days_negotiable": _parse_bool(form_data.is_work_days_negotiable_str, "근무 요일 협의 가능 여부"),
            "is_schedule_based": _parse_bool(form_data.is_schedule_based_str, "일정에 따른 근무 여부"),
            "work_start_time": form_data.work_start_time,
            "work_end_time": form_data.work_end_time,
            "is_work_time_negotiable": _parse_bool(form_data.is_work_time_negotiable_str, "근무 시간 협의 가능 여부"),
            "description": form_data.description,
            "summary": form_data.summary,
            "postings_image": postings_image_url, # 업로드된 이미지 URL 할당
            "latitude": _parse_float(form_data.latitude, "위도"),
            "longitude": _parse_float(form_data.longitude, "경도"),
        }
        # Pydantic 모델(JobPostingCreate) 생성으로 최종 유효성 검사 수행
        job_posting_create_data = JobPostingCreate(**parsed_data)
    except (ValueError, ValidationError) as e:
        # 데이터 파싱 오류 또는 Pydantic 유효성 검사 실패 시 422 에러
        detail = str(e) if isinstance(e, ValueError) else e.errors()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )

    # 3. 서비스 호출하여 공고 생성
    try:
        # 서비스 함수에 검증된 데이터와 사용자 정보 전달
        created_posting = await service.create_job_posting(
            job_posting_data=job_posting_create_data,
            author_id=current_user.id,
            company_id=current_user.company_id,
            repository=repository
        )
        # 성공 시 생성된 공고 정보 반환 (201 응답)
        return created_posting
    except HTTPException as http_exc:
        # 서비스 내부에서 발생시킨 HTTP 예외는 그대로 전달
        raise http_exc
    except Exception as e:
        # 그 외 예상치 못한 서비스 오류 발생 시 500 에러
        logger.exception("채용 공고 생성 서비스 호출 오류") # 예외 정보와 함께 에러 로그 기록
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"채용 공고 생성 처리 중 서버 오류 발생: {e}"
        )


@router.get(
    "/",
    response_model=PaginatedJobPostingResponse,
    summary="채용공고 목록 조회",
    description="채용공고 목록을 페이지네이션하여 조회합니다. 로그인 시 즐겨찾기 여부가 포함됩니다.",
)
async def list_postings(
    skip: int = Query(0, ge=0, description="건너뛸 레코드 수"),
    limit: int = Query(10, ge=1, le=100, description="가져올 레코드 수"),
    current_user: Optional[User] = Depends(get_current_user_optional), # 로그인 사용자 (선택적)
    repository: JobPostingRepository = Depends(get_job_posting_repository)
) -> PaginatedJobPostingResponse:
    """채용공고 목록 조회 API (페이지네이션)"""
    logger.info(f"GET /posting 요청 수신: skip={skip}, limit={limit}, user_id={current_user.id if current_user else None}")
    # 1. 현재 로그인 사용자 ID 추출 (없으면 None)
    user_id = current_user.id if current_user else None
    # 2. 서비스 호출하여 공고 목록 및 전체 개수 조회
    postings, total_count = await service.list_job_postings(
        repository=repository,
        skip=skip, limit=limit, user_id=user_id
    )
    # 3. 페이지네이션 응답 스키마에 맞춰 결과 반환
    return PaginatedJobPostingResponse(
        items=postings,
        total=total_count,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/search",
    response_model=PaginatedJobPostingResponse,
    summary="채용공고 검색",
    description="키워드 및 필터 기반으로 채용공고를 검색합니다. 로그인 시 즐겨찾기 여부가 포함됩니다.",
)
async def search_postings(
    keyword: str | None = Query(None, description="검색 키워드 (제목, 내용, 요약)"),
    location1: str | None = Query(None, description="근무지 지역(시/도)"),
    location2: str | None = Query(None, description="근무지 지역(구/군)"),
    job_category: JobCategoryEnum | None = Query(None, description="직무 카테고리"),
    employment_type: str | None = Query(None, description="고용 형태"),
    is_always_recruiting: bool | None = Query(None, description="상시 채용 여부"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(10, ge=1, le=100, description="페이지당 결과 수"),
    sort: SortOptions = Query(SortOptions.LATEST, description="정렬 기준"),
    current_user: Optional[User] = Depends(get_current_user_optional), # 로그인 사용자 (선택적)
    repository: JobPostingRepository = Depends(get_job_posting_repository)
) -> PaginatedJobPostingResponse:
    """채용공고 검색 API (필터링, 정렬, 페이지네이션)"""
    logger.info(f"GET /posting/search 요청 수신: keyword={keyword}, location1={location1}, location2={location2}, job_category={job_category}, employment_type={employment_type}, is_always_recruiting={is_always_recruiting}, page={page}, limit={limit}, sort={sort}, user_id={current_user.id if current_user else None}")
    # 1. 현재 로그인 사용자 ID 추출 (없으면 None)
    user_id = current_user.id if current_user else None
    # 2. 서비스 호출하여 검색 조건에 맞는 공고 목록 및 전체 개수 조회
    postings, total_count = await service.search_job_postings(
        repository=repository,
        keyword=keyword,
        location1=location1,
        location2=location2,
        job_category=job_category,
        employment_type=employment_type,
        is_always_recruiting=is_always_recruiting,
        page=page,
        limit=limit,
        sort=sort,
        user_id=user_id
    )
    # 3. 페이지네이션 응답 스키마에 맞춰 결과 반환
    return PaginatedJobPostingResponse(
        items=postings,
        total=total_count,
        skip=(page - 1) * limit, # 스킵 계산
        limit=limit,
    )


@router.get(
    "/popular",
    response_model=PaginatedJobPostingResponse,
    summary="인기 채용공고 목록 조회",
    description="지원자 수가 많은 인기 채용공고를 조회합니다. 로그인 시 즐겨찾기 여부가 포함됩니다.",
)
async def list_popular_postings(
    limit: int = Query(10, ge=1, le=100, description="가져올 레코드 수"),
    current_user: Optional[User] = Depends(get_current_user_optional), # 로그인 사용자 (선택적)
    repository: JobPostingRepository = Depends(get_job_posting_repository)
) -> PaginatedJobPostingResponse:
    """인기 채용공고 목록 조회 API (지원자 수 기준)"""
    logger.info(f"GET /posting/popular 요청 수신: limit={limit}, user_id={current_user.id if current_user else None}")
    # 1. 현재 로그인 사용자 ID 추출 (없으면 None)
    user_id = current_user.id if current_user else None
    # 2. 서비스 호출하여 인기 공고 목록 및 개수 조회
    postings, total_count = await service.get_popular_job_postings(
        repository=repository,
        limit=limit, user_id=user_id
    )
    # 3. 페이지네이션 응답 스키마에 맞춰 결과 반환
    return PaginatedJobPostingResponse(
        items=postings,
        total=total_count, # total은 실제 조회된 인기 공고 수
        skip=0, # 인기 공고는 항상 첫 페이지
        limit=limit,
    )


@router.get(
    "/popular-by-my-age",
    response_model=PaginatedJobPostingResponse,
    summary="내 연령대 인기 채용공고 목록 조회",
    description="로그인한 사용자의 나이대에서 인기 있는 공고를 조회합니다. (생년월일 정보 필요)",
)
async def list_popular_postings_by_my_age(
    limit: int = Query(10, ge=1, le=100, description="가져올 레코드 수"),
    current_user: Optional[User] = Depends(get_current_user_optional), # 로그인 필수
    repository: JobPostingRepository = Depends(get_job_posting_repository)
) -> PaginatedJobPostingResponse:
    """사용자 연령대별 인기 채용공고 조회 API"""
    logger.info(f"GET /posting/popular-by-my-age 요청 수신: limit={limit}, user_id={current_user.id if current_user else None}")
    # 1. 로그인 여부 확인 (이 API는 로그인 필수)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다.")
    
    # 2. 서비스 호출하여 연령대에 맞는 인기 공고 목록 및 개수 조회
    # (서비스 내부에서 사용자 생년월일 검증 및 오류 처리)
    postings, total_count = await service.get_popular_job_postings_for_user_age_group(
        user=current_user,
        repository=repository,
        limit=limit
    )
    # 3. 페이지네이션 응답 스키마에 맞춰 결과 반환
    return PaginatedJobPostingResponse(
        items=postings,
        total=total_count, # total은 실제 조회된 인기 공고 수
        skip=0, # 인기 공고는 항상 첫 페이지
        limit=limit,
    )


@router.get(
    "/{job_posting_id}",
    response_model=JobPostingResponse,
    summary="채용공고 상세 조회",
    description="특정 채용공고의 상세정보를 조회합니다. 로그인 시 즐겨찾기 여부가 포함됩니다.",
)
async def get_posting(
    job_posting_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional), # 로그인 사용자 (선택적)
    repository: JobPostingRepository = Depends(get_job_posting_repository)
) -> JobPosting:
    """채용공고 상세 조회 API"""
    logger.info(f"GET /posting/{job_posting_id} 요청 수신: user_id={current_user.id if current_user else None}")
    # 1. 현재 로그인 사용자 ID 추출 (없으면 None)
    user_id = current_user.id if current_user else None
    # 2. 헬퍼 함수 사용하여 공고 조회 (없으면 404 발생)
    posting = await get_posting_or_404(job_posting_id=job_posting_id, user_id=user_id, repository=repository)
    # 3. 조회된 공고 정보 반환
    return posting


@router.patch(
    "/{job_posting_id}",
    response_model=JobPostingResponse,
    summary="채용공고 수정",
    description="로그인된 기업 담당자가 자신이 올린 채용공고를 수정합니다. 이미지 파일을 함께 업로드할 수 있습니다.",
)
async def update_posting(
    job_posting_id: int,
    form_data: JobPostingUpdateFormData = Depends(),
    postings_image: Optional[UploadFile] = File(None, description="채용공고 이미지 파일 (교체 시 업로드, 선택사항)"),
    current_user: CompanyUser = Depends(get_current_company_user),
    repository: JobPostingRepository = Depends(get_job_posting_repository)
) -> JobPosting:
    """채용공고 수정 API"""
    logger.info(f"PATCH /posting/{job_posting_id} 요청 수신")
    db_posting = await repository.get_by_id(job_posting_id)
    if not db_posting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="채용공고를 찾을 수 없습니다.")

    await check_posting_permission(db_posting, current_user, action_type="수정")

    parsed_update_data = {}
    # form_data의 각 필드를 파싱하여 parsed_update_data에 채움 (제공된 경우에만)
    if form_data.title is not None: parsed_update_data["title"] = form_data.title
    if form_data.recruit_period_start is not None: parsed_update_data["recruit_period_start"] = _parse_date(form_data.recruit_period_start, "모집 시작일")
    if form_data.recruit_period_end is not None: parsed_update_data["recruit_period_end"] = _parse_date(form_data.recruit_period_end, "모집 종료일")
    if form_data.is_always_recruiting_str is not None: parsed_update_data["is_always_recruiting"] = _parse_bool(form_data.is_always_recruiting_str, "상시 모집 여부")
    if form_data.education is not None: parsed_update_data["education"] = _parse_enum(EducationEnum, form_data.education, "요구 학력")
    if form_data.recruit_number is not None: parsed_update_data["recruit_number"] = _parse_int(form_data.recruit_number, "모집 인원", min_value=0)
    if form_data.benefits is not None: parsed_update_data["benefits"] = form_data.benefits
    if form_data.preferred_conditions is not None: parsed_update_data["preferred_conditions"] = form_data.preferred_conditions
    if form_data.other_conditions is not None: parsed_update_data["other_conditions"] = form_data.other_conditions
    if form_data.work_address is not None: parsed_update_data["work_address"] = form_data.work_address
    if form_data.work_place_name is not None: parsed_update_data["work_place_name"] = form_data.work_place_name
    if form_data.region1 is not None: parsed_update_data["region1"] = form_data.region1
    if form_data.region2 is not None: parsed_update_data["region2"] = form_data.region2
    if form_data.payment_method is not None: parsed_update_data["payment_method"] = _parse_enum(PaymentMethodEnum, form_data.payment_method, "급여 지급 방식")
    if form_data.job_category is not None: parsed_update_data["job_category"] = _parse_enum(JobCategoryEnum, form_data.job_category, "직종 카테고리")
    if form_data.work_duration is not None: parsed_update_data["work_duration"] = _parse_enum(WorkDurationEnum, form_data.work_duration, "근무 기간")
    if form_data.is_work_duration_negotiable_str is not None: parsed_update_data["is_work_duration_negotiable"] = _parse_bool(form_data.is_work_duration_negotiable_str, "근무 기간 협의 가능 여부")
    if form_data.career is not None: parsed_update_data["career"] = form_data.career
    if form_data.employment_type is not None: parsed_update_data["employment_type"] = form_data.employment_type
    if form_data.salary is not None: parsed_update_data["salary"] = _parse_int(form_data.salary, "급여", min_value=0)
    if form_data.work_days is not None: parsed_update_data["work_days"] = form_data.work_days
    if form_data.is_work_days_negotiable_str is not None: parsed_update_data["is_work_days_negotiable"] = _parse_bool(form_data.is_work_days_negotiable_str, "근무 요일 협의 가능 여부")
    if form_data.is_schedule_based_str is not None: parsed_update_data["is_schedule_based"] = _parse_bool(form_data.is_schedule_based_str, "일정에 따른 근무 여부")
    if form_data.work_start_time is not None: parsed_update_data["work_start_time"] = form_data.work_start_time # 형식 검증은 JobPostingUpdate 모델에서
    if form_data.work_end_time is not None: parsed_update_data["work_end_time"] = form_data.work_end_time # 형식 검증은 JobPostingUpdate 모델에서
    if form_data.is_work_time_negotiable_str is not None: parsed_update_data["is_work_time_negotiable"] = _parse_bool(form_data.is_work_time_negotiable_str, "근무 시간 협의 가능 여부")
    if form_data.description is not None: parsed_update_data["description"] = form_data.description
    if form_data.summary is not None: parsed_update_data["summary"] = form_data.summary
    if form_data.latitude is not None: parsed_update_data["latitude"] = _parse_float(form_data.latitude, "위도")
    if form_data.longitude is not None: parsed_update_data["longitude"] = _parse_float(form_data.longitude, "경도")

    # 이미지 처리 로직
    final_image_url = db_posting.postings_image # 기본값은 기존 이미지 URL
    if postings_image: # 새 파일이 업로드된 경우
        try:
            # 참고: 이전 이미지 파일 삭제 로직은 서비스 계층에서 필요시 처리
            final_image_url = await upload_image_to_ncp(postings_image, folder="job_postings")
        except Exception as e:
            logger.exception("Error uploading new image during job posting update")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"채용공고 이미지 업로드 중 오류 발생: {e}")
    elif form_data.postings_image_url_str is not None: # 새 파일 없고, URL 문자열이 제공된 경우
        if form_data.postings_image_url_str == "": # 빈 문자열이면 이미지 삭제 의도
            final_image_url = None
        else:
            final_image_url = form_data.postings_image_url_str
    # new_postings_image_file도 없고, postings_image_url_str도 제공되지 않으면 기존 이미지(final_image_url) 유지
    
    parsed_update_data["postings_image"] = final_image_url

    try:
        # JobPostingUpdate 모델을 사용하여 최종 유효성 검사 및 데이터 준비
        # 여기서 **parsed_update_data 언패킹 시 None 값도 전달되어 모델의 Optional 필드에 반영됨
        job_posting_update_model = JobPostingUpdate(**parsed_update_data) 
    except (ValueError, ValidationError) as e:
        detail = str(e) if isinstance(e, ValueError) else e.errors()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

    updated_posting = await service.update_job_posting(
        job_posting_id=job_posting_id,
        data=job_posting_update_model, # Pydantic 모델로 변환된 데이터 전달
        repository=repository
    )
    
    return updated_posting


@router.delete(
    "/{job_posting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="채용공고 삭제",
    description="로그인된 기업 담당자가 자신이 올린 채용공고를 삭제합니다.",
)
async def delete_posting(
    job_posting_id: int,
    current_user: CompanyUser = Depends(get_current_company_user), # 현재 로그인한 기업 사용자
    repository: JobPostingRepository = Depends(get_job_posting_repository) # 공고 조회 및 서비스 호출 시 필요
) -> None:
    """채용공고 삭제 API"""
    logger.info(f"DELETE /posting/{job_posting_id} 요청 수신")
    # 1. 공고 ID로 공고 조회 (레포지토리 직접 사용, 없으면 404)
    posting = await repository.get_by_id(job_posting_id)
    if not posting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="삭제할 채용공고를 찾을 수 없습니다.")

    # 2. 삭제 권한 확인 (헬퍼 함수 사용, 없으면 403)
    await check_posting_permission(posting, current_user, action_type="삭제")

    # 3. 서비스 호출하여 공고 삭제
    success = await service.delete_job_posting(
        job_posting_id=job_posting_id,
        repository=repository
    )
    # 4. 서비스 결과 확인 및 오류 처리
    if not success:
        # 서비스 내부 DB 오류 등으로 삭제 실패 시 500 에러
        # (삭제 대상이 없는 경우는 이미 1단계에서 404 처리됨)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채용 공고 삭제 중 오류가 발생했습니다."
        )
    # 5. 성공 시 응답 없음 (자동으로 204 No Content 반환)