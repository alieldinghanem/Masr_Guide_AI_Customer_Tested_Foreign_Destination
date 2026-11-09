"""Bound real incoming HTTP request bodies before JSON parsing.

Content-Length is only a client assertion. This ASGI middleware counts received
bytes including chunked/streaming bodies; an attacker cannot bypass the limit
by omitting or lying about the header. No request body is persisted or logged.
"""
from starlette.responses import JSONResponse

MAX_API_BODY_BYTES = 512 * 1024


class LimitApiBody:
    def __init__(self, app, max_bytes: int = MAX_API_BODY_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or not scope.get('path', '').startswith('/api/'):
            return await self.app(scope, receive, send)

        def oversized_response():
            return JSONResponse({'detail': 'Request body exceeds the 512 KB API limit'},
                                status_code=413, headers={'Cache-Control': 'no-store'})

        declared = next((v for k, v in scope.get('headers', []) if k.lower() == b'content-length'), None)
        if declared is not None:
            try:
                if int(declared) > self.max_bytes:
                    return await oversized_response()(scope, receive, send)
            except ValueError:
                # Don't trust a malformed header; the receive-byte check remains authoritative.
                pass

        chunks = []
        size = 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            if message['type'] != 'http.request':
                continue
            size += len(message.get('body', b''))
            if size > self.max_bytes:
                return await oversized_response()(scope, receive, send)
            chunks.append(message)
            if not message.get('more_body', False):
                break

        index = 0

        async def replay():
            nonlocal index
            if index < len(chunks):
                message = chunks[index]
                index += 1
                return message
            return {'type': 'http.disconnect'}

        return await self.app(scope, replay, send)
