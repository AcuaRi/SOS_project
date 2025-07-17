from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

# 기존 Yun/db.py에서 get_db 함수를 import 합니다.
from Yun.db import SessionLocal as get_db_session # SessionLocal을 get_db_session으로 별칭 변경
from login import schemas, crud, auth, models # models도 import하여 테이블 생성에 사용

router = APIRouter(
    prefix="/auth", # 모든 엔드포인트 앞에 /auth가 붙습니다. (예: /auth/register)
    tags=["Authentication"]
)

# Dependency to get DB session
def get_db():
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()

@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    # crud.create_user 함수는 이제 해싱된 비밀번호를 직접 받지 않고, 내부에서 해싱합니다.
    new_user = crud.create_user(db=db, user=user)
    return new_user

@router.post("/login")
def login_user(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    
    # 로그인 성공 시, 여기에서 JWT 토큰 등을 생성하여 반환할 수 있습니다.
    # 지금은 간단히 성공 메시지를 반환합니다.
    return RedirectResponse(url="http://35.78.251.74:8000/web/chat.html", status_code=status.HTTP_302_FOUND)

# 데이터베이스 테이블이 존재하지 않을 경우 생성 (개발 단계에서 유용)
# 실제 운영 환경에서는 Alembic과 같은 마이그레이션 도구를 사용하는 것이 좋습니다.
@router.on_event("startup")
def create_db_tables():
    models.Base.metadata.create_all(bind=get_db_session().bind)
