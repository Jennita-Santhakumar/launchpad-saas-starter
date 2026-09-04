from starlette.requests import Request

from app.core.rate_limit import workspace_key_func


def _make_request(path_params: dict, client_host: str = "127.0.0.1") -> Request:
    scope = {
        "type": "http",
        "path_params": path_params,
        "client": (client_host, 1234),
        "headers": [],
    }
    return Request(scope)


def test_workspace_key_func_uses_workspace_id_when_present():
    request = _make_request({"workspace_id": "11111111-1111-1111-1111-111111111111"})
    assert workspace_key_func(request) == "workspace:11111111-1111-1111-1111-111111111111"


def test_workspace_key_func_falls_back_to_ip_without_workspace_id():
    request = _make_request({})
    assert workspace_key_func(request) == "127.0.0.1"
