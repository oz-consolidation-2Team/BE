import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import ALGORITHM, SECRET_KEY
from app.core.db import get_db_session
from app.models.company_users import CompanyUser


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
        user_id: str = payload.get("sub")  # sub 클레임에서 사용자 ID 추출
        if user_id is None:
            raise HTTPException(status_code=401, detail="잘못된 토큰입니다.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="토큰 검증 실패.")

    # 데이터베이스에서 회사 사용자 조회
    result = await db.execute(
        select(CompanyUser).filter(CompanyUser.id == int(user_id))
    )
    company_user = result.scalar_one_or_none()
    
    if company_user is None:
        raise HTTPException(status_code=404, detail="기업 사용자를 찾을 수 없습니다.")
    
    return company_user


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
