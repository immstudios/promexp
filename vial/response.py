import json
from http import HTTPStatus


def format_status(code):
    return f"{code} {HTTPStatus(code).phrase}"


def response_type(func):
    def wrapper(parent, body=None, status=200, custom_headers={}):
        body, headers = func(parent, body, status)

        headers["Server"] = "Vial"
        headers["Content-Length"] = len(body)
        headers.update(custom_headers)

        full_headers = []
        for key, value in headers.items():
            full_headers.append((key, str(value)))

        return format_status(status), full_headers, body
    return wrapper


class VResponse():
    @response_type
    def text(self, body, status):
        if body is None:
            r = "Status" if status < 400 else "Error"
            body = f"{r} {status}: {HTTPStatus(status).description}"
        body = body.encode("utf-8")
        headers = {"Content-Type" : "text/txt"}
        return body, headers

    @response_type
    def json(self, body, status):
        body = json.dumps(body).encode("utf-8")
        headers = {"Content-Type" : "application/json"}
        return body, headers

    @response_type
    def raw(self, body, status):
        headers = {"Content-Type" : "application/octet-stream"}
        if type(body) == bytes:
            return body, headers
        elif type.body == str:
            return body.encode("utf-8"), headers
        else:
            return str(body).encode("utf-8"), headers
