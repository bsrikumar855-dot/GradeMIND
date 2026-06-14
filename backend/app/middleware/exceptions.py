import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.middleware.exceptions")


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers on the FastAPI application instance.
    """
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Format the validation errors
        errors = exc.errors()
        error_messages = []
        for err in errors:
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            error_messages.append(f"[{loc}]: {msg}")
            
            # Clean non-serializable items inside "ctx" (e.g. ValueError or Exception objects)
            if "ctx" in err and isinstance(err["ctx"], dict):
                cleaned_ctx = {}
                for k, v in err["ctx"].items():
                    if isinstance(v, (str, int, float, bool, type(None))):
                        cleaned_ctx[k] = v
                    else:
                        cleaned_ctx[k] = str(v)
                err["ctx"] = cleaned_ctx
        
        detail_msg = "Validation failed: " + "; ".join(error_messages)
        
        try:
            from datetime import datetime
            with open("d:\\GradeMIND\\backend\\debug.log", "a", encoding="utf-8") as f:
                f.write(f"--- VALIDATION ERROR: {datetime.now()} ---\n")
                f.write(f"Errors: {errors}\n\n")
        except Exception:
            pass

        return JSONResponse(
            status_code=422,
            content={"detail": detail_msg, "errors": errors}
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Log the full stack trace for internal server errors
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        
        try:
            import traceback
            from datetime import datetime
            with open("d:\\GradeMIND\\backend\\debug.log", "a", encoding="utf-8") as f:
                f.write(f"--- UNHANDLED EXCEPTION: {datetime.now()} ---\n")
                f.write(traceback.format_exc())
                f.write("\n")
        except Exception:
            pass

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

