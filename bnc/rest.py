from dataclasses import dataclass

import requests
import json
import time
from urllib.parse import urlencode

@dataclass
class Request:
    """Generic request structure for API calls."""
    base_url: str 
    path: str
    method: str = "GET"
    headers: dict[str, str] = None
    params: dict[str, any] = None
    api_key: str = None
    resp_in_microseconds: bool = False
    retry: int = 0


@dataclass 
class Response[DataType=dict|list|None]:
    """Generic response structure from API calls."""
    status_code: int = None
    status: str = None
    code: int = None
    msg: str = None
    data: DataType = None
    
    
def tidy_request_params(params: dict[str, any]) -> dict[str, any]:
    params = {k: v for k, v in params.items() if v is not None}
    for k, v in params.items():
        if isinstance(v, bool):
            params[k] = str(v).lower()
        elif isinstance(v, list) and len(v) > 0:
            s = "["
            for i, item in enumerate(v):
                if isinstance(item, str):
                    s += f'"{item}",'
                else:
                    s += str(item)
            # remove last comma
            s = s[:-1]
            s += "]"
            params[k] = s
    return params


def request[DataType](req: Request) -> Response[DataType]:
    """Makes an HTTP request and handles the response.
    
    Args:
        req: The request configuration
        params: Request parameters
        
    Returns:
        Response object containing status and data
        
    Raises:
        ValueError: If request fails after max retries
    """

    # Build URL with query params
    url = req.base_url + req.path
    if req.params:
        params = tidy_request_params(req.params)
        url += f"?{urlencode(params)}"
        
    # Make request
    try:
        if req.resp_in_microseconds:
            req.headers["X-MBX-TIME-UNIT"] = "MICROSECOND"
            
        response = requests.request(
            method=req.method,
            url=url, 
            headers=req.headers
        )

        # Parse response body
        body = response.content
        status_code = response.status_code
        
        # Create response object
        resp = Response[DataType](
            status_code=status_code,
            status=response.reason,
            code=0,
            msg="",
            data=None
        )

        # Handle non-200 status codes
        if status_code != 200:
            try:
                error_data = json.loads(body)
                resp.code = error_data.get("code", 0)
                resp.msg = error_data.get("msg", "")
                
                # Handle timestamp outside recvWindow error
                if resp.code == -1021 and req.retry < 5:
                    time.sleep(1)
                    req.retry += 1
                    return request(req)
                    
            except json.JSONDecodeError:
                raise Exception(f"Failed to parse error response: {body}")
                
            raise Exception(f"Request failed: {resp.code} {resp.msg}")

        # Parse successful response
        try:
            if body:
                resp.data = json.loads(body)
            return resp
        except json.JSONDecodeError:
            raise Exception(f"Failed to parse success response: {body}")

    except requests.exceptions.ConnectionError as e:
        # Retry on connection errors
        if req.retry < 5:
            time.sleep(1)
            req.retry += 1
            return request(req)
        raise Exception(f"Request failed after {req.retry} retries") from e

