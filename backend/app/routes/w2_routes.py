from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
import shutil, os, logging
from tempfile import NamedTemporaryFile
from app.w2_parser import W2Parser
from app.errors import UnsupportedFileTypeError, W2ParseError

router = APIRouter(prefix="/w2", tags=["w2"])
logger = logging.getLogger("w2")
parser = W2Parser()

ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg"}

@router.post("/upload")
async def upload_w2(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail=f"Unsupported file type {file.content_type}")
    try:
        tmp_file = NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1])
        with tmp_file as tmp:
            shutil.copyfileobj(file.file, tmp)
        parsed, ftype = parser.parse_file(tmp_file.name, file.content_type)
        return {"file_type": ftype, "parsed_data": parsed}
    except W2ParseError as e:
        logger.warning("W2 parse error: %s", e)
        raise HTTPException(status_code=422, detail=f"Unable to parse W-2: {e}")
    except Exception as e:
        logger.exception("Unexpected error parsing W2: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error while parsing W-2")
