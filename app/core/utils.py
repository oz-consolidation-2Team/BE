import bcrypt, jwt, boto3, uuid, os
from fastapi import Depends, Header, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import ALGORITHM, SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES
from app.core.db import get_db_session
from app.models.company_users import CompanyUser
from app.models.users import User

# NCP Object Storage 접속 정보
NCP_ACCESS_KEY = os.getenv("NCP_ACCESS_KEY")
NCP_SECRET_KEY = os.getenv("NCP_SECRET_KEY")
NCP_BUCKET_NAME = os.getenv("NCP_BUCKET_NAME")
NCP_ENDPOINT = os.getenv("NCP_ENDPOINT", "https://kr.object.ncloudstorage.com")
NCP_REGION = os.getenv("NCP_REGION", "kr-standard")

# 인증된 회사 사용자 반환 (JWT 토큰 기반)
async def get_current_company_user(
    Authorization: str = Header(...), db: AsyncSession = Depends(get_db_session)
) -> CompanyUser:
    """
    Authorization 헤더의 JWT 토큰을 검증하고 해당하는 기업 사용자를 반환합니다.
    유효하지 않은 토큰이거나 사용자가 없는 경우 HTTP 예외가 발생합니다.
    """
    # 헤더에서 Bearer 토큰 추출
    if Authorization.startswith("Bearer "):
        token = Authorization.split(" ")[1]
    else:
        raise HTTPException(status_code=401, detail="토큰이 제공되지 않았습니다.")
    
    try:
        # JWT 토큰 디코딩
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email: str = payload.get("sub")  # sub 클레임에서 사용자 email 추출
        if user_email is None:
            raise HTTPException(status_code=401, detail="잘못된 토큰입니다.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="토큰 검증 실패.")

    # 데이터베이스에서 회사 사용자 조회
    result = await db.execute(
        select(CompanyUser).filter_by(email=user_email)
    )
    company_user = result.scalar_one_or_none()
    
    if company_user is None:
        raise HTTPException(status_code=404, detail="기업 사용자를 찾을 수 없습니다.")
    
    return company_user

# 인증된 일반 사용자 반환 (선택적, JWT 'sub' 클레임의 이메일 기준)
async def get_current_user_optional(
    Authorization: Optional[str] = Header(None), db: AsyncSession = Depends(get_db_session)
) -> Optional[User]:
    """
    Authorization 헤더의 JWT 토큰을 검증하고 해당하는 일반 사용자를 반환합니다.
    토큰이 없거나 유효하지 않으면 None을 반환합니다.
    JWT 'sub' 클레임에 저장된 사용자 이메일을 사용하여 사용자를 찾습니다.
    """
    if Authorization is None or not Authorization.startswith("Bearer "):
        return None

    token = Authorization.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_sub = payload.get("sub")
        if user_sub is None:
            print("경고: JWT 페이로드에 'sub' 클레임이 없습니다.")
            return None
    except jwt.ExpiredSignatureError:
        print("경고: JWT 토큰이 만료되었습니다.")
        return None
    except jwt.PyJWTError as e:
        print(f"경고: JWT 검증 실패 - {e}")
        return None
    except Exception as e:
        print(f"JWT 디코딩 또는 페이로드 접근 중 오류 발생: {e}")
        return None

    # user_sub이 숫자면 id로, 아니면 이메일로 조회
    try:
        if user_sub.isdigit():
            result = await db.execute(
                select(User).filter(User.id == int(user_sub))
            )
        else:
            result = await db.execute(
                select(User).filter(User.email == user_sub)
            )
        user = result.scalar_one_or_none()
        return user
    except Exception as e:
        print(f"DB에서 사용자 조회 중 오류 발생: {e}")
        return None

def hash_password(password: str) -> str:
    """비밀번호를 bcrypt 해시로 변환"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """입력한 비밀번호와 해시가 일치하는지 확인"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )

async def upload_image_to_ncp(file: UploadFile, folder: str = "job_postings"):
    """
    이미지 파일을 NCP Object Storage에 업로드하고 URL을 반환
    
    Args:
        file: 업로드할 파일 객체
        folder: 저장할 폴더 경로
        
    Returns:
        str: 업로드된 파일의 URL
    """
    if not file:
        return None
        
    # 파일 확장자 확인
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ['.jpg', '.jpeg', '.png', '.gif']:
        raise ValueError("지원되지 않는 이미지 형식입니다.")
    
    # 고유한 파일명 생성
    today = datetime.now().strftime("%Y%m%d")
    unique_filename = f"{folder}/{today}_{uuid.uuid4()}{file_ext}"
    
    # S3 클라이언트 생성 (NCP Object Storage는 S3 호환)
    s3_client = boto3.client(
        's3',
        endpoint_url=NCP_ENDPOINT,
        aws_access_key_id=NCP_ACCESS_KEY,
        aws_secret_access_key=NCP_SECRET_KEY,
        region_name=NCP_REGION
    )
    
    # 파일 데이터 읽기
    contents = await file.read()
    
    # 파일 업로드 (ACL='public-read' 추가)
    s3_client.put_object(
        Bucket=NCP_BUCKET_NAME,
        Key=unique_filename,
        Body=contents,
        ContentType=file.content_type,
        ACL='public-read'
    )
    
    # 업로드된 파일의 URL 생성
    url = f"{NCP_ENDPOINT}/{NCP_BUCKET_NAME}/{unique_filename}"
    
    return url

# JWT 토큰 생성 함수들
async def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    # 액세스 토큰을 생성하는 비동기 함수
    to_encode = data.copy()  # 인코딩할 데이터를 복사
    if expires_delta:
        expire = (
            datetime.now() + expires_delta
        )  # 주어진 만료기간을 이용하여 만료 시각 계산
    else:
        expire = datetime.now() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )  # 기본 만료 시간 설정
    to_encode.update({"exp": expire})  # 만료 정보 추가
    encoded_jwt = jwt.encode(
        to_encode, SECRET_KEY, algorithm=ALGORITHM
    )  # JWT 토큰 생성
    return encoded_jwt  # 생성된 토큰 반환


async def create_refresh_token(data: dict) -> str:
    # 리프레쉬 토큰을 생성하는 비동기 함수
    expire = datetime.now() + timedelta(
        minutes=REFRESH_TOKEN_EXPIRE_MINUTES
    )  # 리프레쉬 토큰 만료시간 계산
    data.update({"exp": expire})  # 만료 정보 추가
    encoded_jwt = jwt.encode(
        data, SECRET_KEY, algorithm=ALGORITHM
    )  # 리프레쉬 토큰 생성
    return encoded_jwt  # 생성된 토큰 반환