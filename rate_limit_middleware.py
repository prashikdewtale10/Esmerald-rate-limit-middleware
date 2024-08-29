import time
import structlog

from collections import defaultdict
from typing import Any, Coroutine
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Receive, Scope, Send
from esmerald.requests import Request

logger = structlog.get_logger("common")


class RateLimitMiddleware(MiddlewareProtocol):
    """
    Middleware to enforce rate limiting on incoming requests.

    This middleware limits the number of requests a client \
        (identified by IP address)
    can make to the server within a specified time window. \
        If the client exceeds the
    allowed number of requests, a `PermissionDenied` exception is raised.

    Attributes:
        - max_calls (int): Maximum number of requests allowed within \
            the time window.
        time_window (int): Time window (in seconds) during which `max_calls` \
            is enforced.
        cache (defaultdict): Dictionary to store request counts and timestamps\
            per IP address.

    Args:
        app (ASGIApp): The ASGI application to which this \
            middleware is applied.

        **kwargs: Additional keyword arguments to be passed to the superclass.

    Steps Performed:
        1. **Extract Client IP**: Retrieve the IP address of the client \
            making the request.
        2. **Check Rate Limit**:
            - Compare the current timestamp with the timestamp of the \
                last request from the client.
            - If the time window has passed, reset the count and timestamp \
                for the client.
            - If the client has made fewer requests than allowed, increment \
                the request count.
            - If the client exceeds the rate limit, raise a `PermissionDenied`\
                exception.
        3. **Forward Request**: Pass the request to the next ASGI application\
            or middleware.

    Raises:
        PermissionDenied: If the client exceeds the allowed number of \
            requests within the time window.

    Example:
        app = Esmerald()
        app.add_middleware(RateLimitMiddleware, max_calls=5, time_window=60)
    """
    def __init__(self, app: ASGIApp, max_calls: int,
                 time_window: int, **kwargs):
        super().__init__(app, **kwargs)
        self.app = app
        self.max_calls = max_calls
        self.time_window = time_window
        self.cache = defaultdict(int)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> Coroutine[Any, Any, None]: # noqa
        request = Request(scope=scope, receive=receive, send=send)
        logger.info(f"requested url: {request.url}")
        ip = request.client.host
        current_timestamp = time.time()
        if current_timestamp - self.cache[ip] >= self.time_window:
            self.cache[ip] = current_timestamp
            self.cache[(ip, 'count')] = 1
        elif self.cache[(ip, 'count')] < self.max_calls:
            self.cache[(ip, 'count')] += 1
        else:
            # here raise expection with status code 429
            print("You've reached our limit of messages")

        return await self.app(scope, receive, send)




