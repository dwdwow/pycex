import asyncio
import requests
import json
import time
from urllib.parse import urlencode

from cex.bnc.sign import sign_by_hmac_sha256_to_hex

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


class RequestError(Exception):
    def __init__(self,
                 url: str,
                 http_status_code: int=None,
                 bnc_code: int=None,
                 bnc_msg: str=None,
                 exception: Exception=None,
                 resp_body: bytes=None):
        self.url = url
        self.http_status_code = http_status_code
        self.bnc_code = bnc_code
        self.bnc_msg = bnc_msg
        self.exception = exception
        self.resp_body = resp_body
        if not http_status_code:
            super().__init__(f"bnc: RequestException: {url} {exception}")
        elif not bnc_code:
            super().__init__(f"bnc: RequestException: {url} {http_status_code} {exception} {resp_body}")
        else:
            super().__init__(f"bnc: RequestException: {url} {http_status_code} {bnc_code} {bnc_msg}")

    def url(self) -> str:
        return self.url
    
    def http_status_code(self) -> int:
        return self.http_status_code
    
    def bnc_code(self) -> int:
        return self.bnc_code
    
    def bnc_msg(self) -> str:
        return self.bnc_msg
    
    def exception(self) -> Exception:
        return self.exception
    
    def resp_body(self) -> str:
        return self.resp_body


async def request[DataType=dict|list|None](
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] = None,
    params: dict[str, any] = None,
    resp_in_microseconds: bool = False,
    api_private_key: str = None,
    _retried: int = 0) -> DataType:
    """Makes an HTTP request and handles the response.
    
    Args:
        req: The request configuration
        params: Request parameters
        
    Returns:
        Response object containing status and data
        
    Raises:
        RequestError: If request fails after max retries
    """

    url = base_url + path
    if params:
        params = tidy_request_params(params)
        quries = urlencode(params)
        if api_private_key:
            quries += f"&timestamp={int(time.time()*1000)}"
            quries += f"&signature={sign_by_hmac_sha256_to_hex(quries, api_private_key)}"
        url += f"?{quries}"

    if resp_in_microseconds:
        headers["X-MBX-TIME-UNIT"] = "MICROSECOND"
        
    try:
        response = await asyncio.to_thread(requests.request, method=method, url=url, headers=headers)
    except requests.exceptions.ConnectionError as e:
        # Retry on connection errors
        if _retried < 5:
            await asyncio.sleep(1)
            _retried += 1
            return await request(base_url, path, method=method, headers=headers, params=params, resp_in_microseconds=resp_in_microseconds, api_private_key=api_private_key, _retried=_retried)
        raise RequestError(url, exception=e)
    
    status_code = response.status_code
    body = response.content
    
    if status_code != 200:
        try:
            error_data = json.loads(body)
        except json.JSONDecodeError as e:
            raise RequestError(url, http_status_code=status_code, exception=e, resp_body=body)
        code = error_data.get("code", 0)
        msg = error_data.get("msg", "")
        # Handle timestamp outside recvWindow error
        if code == -1021 and _retried < 5:
            await asyncio.sleep(1)
            _retried += 1
            return await request(base_url, path, method=method, headers=headers, params=params, resp_in_microseconds=resp_in_microseconds, api_private_key=api_private_key, _retried=_retried)
        raise RequestError(url, http_status_code=status_code, bnc_code=code, bnc_msg=msg)

    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise RequestError(url, http_status_code=status_code, exception=e, resp_body=body)


