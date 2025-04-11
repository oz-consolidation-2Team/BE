import os
from dotenv import load_dotenv # .env 파일 로드 지원

load_dotenv()

# 데이터베이스 연결 URL
DATABASE_URL = os.getenv("DATABASE_URL")

# 애플리케이션 시크릿 키 (JWT 토큰 서명 등에 사용)
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key_for_safety")

# 현재 실행 환경 구분용 변수 
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

# # 이메일 전송 관련 환경 변수
# EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.naver.com")
# EMAIL_PORT = int(os.getenv("EMAIL_PORT", "465"))
# EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "True") == "True"
# EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
# EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
# DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")
#
# # 이메일 인증/비밀번호 재설정 링크에서 사용할 사이트 URL
# SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")