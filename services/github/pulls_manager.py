import requests
from config import TIMEOUT, PER_PAGE
from services.github.github_manager import create_headers
from utils.handle_exceptions import handle_exceptions


@handle_exceptions(default_return_value=("", ""), raise_on_error=False)
def get_pull_request(url: str, token: str):
    """https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#get-a-pull-request"""
    headers = create_headers(token=token)
    res = requests.get(url=url, headers=headers, timeout=TIMEOUT)
    res.raise_for_status()
    res_json = res.json()
    title: str = res_json["title"]
    body: str = res_json["body"]
    return title, body


@handle_exceptions(default_return_value=None, raise_on_error=False)
def get_pull_request_files(url: str, token: str):
    """https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests-files"""
    headers = create_headers(token=token)
    changes: list[dict[str, str]] = []
    page = 1
    while True:
        params = {"per_page": PER_PAGE, "page": page}
        response = requests.get(
            url=url, headers=headers, params=params, timeout=TIMEOUT
        )
        response.raise_for_status()
        files = response.json()
        if not files:
            break
        for file in files:
            if "patch" not in file:
                continue
            filename, status, patch = file["filename"], file["status"], file["patch"]
            changes.append({"filename": filename, "status": status, "patch": patch})
        page += 1
    return changes
