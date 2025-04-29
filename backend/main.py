import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse, FileResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import uuid
import aiofiles
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
FILE_STORAGE = "uploaded_files"
os.makedirs(FILE_STORAGE, exist_ok=True)

# Use PBKDF2 instead of bcrypt to avoid issues
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_type: Optional[str] = None

class User(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    user_type: str

class UserInDB(User):
    hashed_password: str

# Fake database with pre-hashed passwords
fake_users_db = {
    "opsuser": {
        "username": "opsuser",
        "email": "ops@example.com",
        "full_name": "Operation User",
        "hashed_password": pwd_context.hash("secret"),
        "disabled": False,
        "user_type": "ops"
    },
    "clientuser": {
        "username": "clientuser",
        "email": "client@example.com",
        "full_name": "Client User",
        "hashed_password": pwd_context.hash("secret"),
        "disabled": False,
        "user_type": "client"
    }
}

files_db = {}
download_tokens_db = {}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "File Sharing API is running"}

# Utility functions
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_type: str = payload.get("user_type")
        if username is None or user_type is None:
            raise credentials_exception
        token_data = TokenData(username=username, user_type=user_type)
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_ops_user(current_user: User = Depends(get_current_user)):
    if current_user.user_type != "ops":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only operation users can perform this action",
        )
    return current_user

async def get_current_client_user(current_user: User = Depends(get_current_user)):
    if current_user.user_type != "client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only client users can perform this action",
        )
    return current_user

def validate_file_type(filename: str):
    ext = os.path.splitext(filename)[1].lower()
    allowed_extensions = {".pptx", ".docx", ".xlsx"}
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .pptx, .docx, .xlsx files are allowed",
        )

# Routes
@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_type": user.user_type},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/ops/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_ops_user),
):
    validate_file_type(file.filename)
    
    file_id = str(uuid.uuid4())
    file_path = os.path.join(FILE_STORAGE, file_id)
    
    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)
    
    file_info = {
        "file_id": file_id,
        "filename": file.filename,
        "uploaded_by": current_user.username,
        "upload_date": str(datetime.utcnow()),
        "file_path": file_path,
    }
    files_db[file_id] = file_info
    
    return {"message": "File uploaded successfully", "file_id": file_id}

@app.get("/client/files")
async def list_files(current_user: User = Depends(get_current_client_user)):
    return list(files_db.values())

@app.get("/client/download/{file_id}")
async def get_download_link(
    file_id: str,
    current_user: User = Depends(get_current_client_user),
):
    if file_id not in files_db:
        raise HTTPException(status_code=404, detail="File not found")
    
    download_token = str(uuid.uuid4())
    download_tokens_db[download_token] = {
        "file_id": file_id,
        "user_id": current_user.username,
        "expires": str(datetime.utcnow() + timedelta(minutes=30)),
    }
    
    return {
        "download_link": f"/download-file/{download_token}",
        "message": "success",
    }

@app.get("/download-file/{token}")
async def download_file(token: str):
    if token not in download_tokens_db:
        raise HTTPException(status_code=404, detail="Invalid download link")
    
    file_id = download_tokens_db[token]["file_id"]
    if file_id not in files_db:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_info = files_db[file_id]
    return FileResponse(
        file_info["file_path"],
        filename=file_info["filename"],
        media_type="application/octet-stream",
    )

@app.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user