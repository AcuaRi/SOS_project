from sqlalchemy.orm import Session
from login import models, schemas
from login.auth import hash_password

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = hash_password(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db_sos_friends = models.sos_friends(email=user.email)
    db.add(db_user)
    db.commit()
    db.add(db_sos_friends) 
    db.commit()
    db.refresh(db_user)
    return db_user

# #def create_sos_friends(db: Session, email: str):
#     #return db.query(models.sos_friends).filter(models.User.email == email).first()

#  #   db_user = models.User(email=user.email)
#   #\  db.add(db_user)
#     db.commit()
#     db.refresh(db_user)
#     return db_user