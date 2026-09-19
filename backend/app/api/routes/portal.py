from typing import Annotated
from fastapi import APIRouter, Depends, Header
from app.core.errors import ApiError
from app.core.security import bearer
from app.services import declarations
from app.models import FileAsset
from app.api.routes.extension import DB, Key, binary
from app.schemas.extension import PortalInput
router=APIRouter(prefix='/simulation-portal',tags=['local-simulation'])


def token(creds=Depends(bearer)):
    if not creds:raise ApiError(401,'UNAUTHENTICATED','缺少申报访问凭证')
    return creds.credentials
Token=Annotated[str,Depends(token)]


@router.get('/context')
def context(db:DB,access:Token):
    _,company,dec=declarations.resolve_token(db,access)
    return declarations.context(db,company,dec)


@router.post('/declarations')
def accept(body:PortalInput,db:DB,access:Token,idempotency_key:Key=None):
    body=body.model_dump()
    user,company,dec=declarations.resolve_token(db,access,write=True)
    return declarations.accept(db,user,company,dec,body,idempotency_key)


@router.get('/declarations/{value}/receipt')
def receipt(value:str,db:DB,access:Token):
    _,_,dec=declarations.resolve_token(db,access)
    if value!=str(dec.id):raise ApiError(403,'FORBIDDEN','无权访问此回执')
    if not dec.receipt_file_id:raise ApiError(425,'FILE_NOT_READY','回执尚未就绪')
    return binary(db.get(FileAsset,dec.receipt_file_id))
