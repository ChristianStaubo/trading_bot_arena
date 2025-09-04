from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.requests import Request
import json


class TransformResponseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Skip transformation for FastAPI internal endpoints
        skip_paths = ["/openapi.json", "/docs", "/redoc"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return response

        # Skip non-JSON responses (check content-type header)
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return response

        # Skip if response is already transformed (check if it has our structure)
        try:
            # Read the response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            # Try to parse as JSON
            try:
                body = json.loads(response_body.decode())
            except Exception:
                # If we can't parse as JSON, return original response
                return Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=response.headers,
                    media_type=response.media_type
                )

            # Check if already transformed (has our structure)
            if isinstance(body, dict) and all(key in body for key in ["statusCode", "message", "data"]):
                return JSONResponse(content=body, status_code=response.status_code)

            # Transform the response
            transformed = {
                "statusCode": response.status_code,
                "message": "OK" if 200 <= response.status_code < 300 else "Error",
                "data": body,
            }

            return JSONResponse(content=transformed, status_code=response.status_code)

        except Exception as e:
            # If anything goes wrong, return the original response
            return response
