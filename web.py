import urllib.request
import concurrent.futures
import asyncio
import http.server

async def open(url, data=None, headers={}, f=urllib.request.urlopen):
    request = urllib.request.Request(url, data, headers)
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        response = await loop.run_in_executor(pool, f, request)
        return await loop.run_in_executor(pool, response.read)

async def serve(port):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.server.result = self

        def log_message(self, format, *args):
            pass

    server = http.server.HTTPServer(('', port), Handler)
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        await loop.run_in_executor(pool, server.handle_request)
        server.server_close()
        return server.result