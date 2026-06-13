from typing import Any, Optional
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


def success_response(
    data: Any = None,
    message: str = "Operation successful",
    status_code: int = 200
) -> JSONResponse:
    """
    Generate a standardized success API response.
    """
    content = {
        "success": True,
        "message": message,
        "data": data if data is not None else {}
    }
    return JSONResponse(status_code=status_code, content=jsonable_encoder(content))


def error_response(
    message: str = "Something went wrong",
    status_code: int = 400,
    errors: Any = None
) -> JSONResponse:
    """
    Generate a standardized error API response.
    """
    content = {
        "success": False,
        "message": message
    }
    if errors is not None:
        content["errors"] = errors
        
    return JSONResponse(status_code=status_code, content=jsonable_encoder(content))

