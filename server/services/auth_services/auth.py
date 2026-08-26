import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

security = HTTPBearer()

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_PUBLISHABLE_KEY"),
)

# credentials: The variable name that holds the result.
# : HTTPAuthorizationCredentials | None: A type hint in Python. 
# = Depends(security): Before running this function, run the security helper first
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials 

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})

    try:
        response = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})

    if response.user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    return response.user


def get_user_database(credentials: HTTPAuthorizationCredentials = Depends(security), current_user=Depends(get_current_user)):
    token = credentials.credentials 
    

    user_supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_PUBLISHABLE_KEY"))

    # Verifies the Bearer token.
    user_supabase.postgrest.auth(token)

    return user_supabase
