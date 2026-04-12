from __future__ import annotations

import logging
from typing import Any

import requests

from .. import session_store
from ..config import load_api_base

logger = logging.getLogger("jobhub.client")


class ApiError(Exception):
    def __init__(self, message: str, status: int | None = None, body: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


def _base() -> str:
    return load_api_base()


def _headers() -> dict[str, str]:
    h = {"Accept": "application/json"}
    t = session_store.get_token()
    if t:
        h["Authorization"] = f"Bearer {t}"
    return h


def _request(method: str, path: str, **kwargs: Any) -> Any:
    url = f"{_base()}{path}"
    headers = _headers()
    if "files" in kwargs:
        r = requests.request(method, url, headers=headers, timeout=120, **kwargs)
    else:
        r = requests.request(method, url, headers=headers, timeout=60, **kwargs)
    if r.status_code >= 400:
        logger.debug("HTTP %s %s -> %s", method, url, r.status_code)
        try:
            body = r.json()
        except Exception:
            body = r.text
        msg = str(body)
        if isinstance(body, dict) and "detail" in body:
            d = body["detail"]
            msg = str(d) if not isinstance(d, list) else "; ".join(str(x) for x in d)
        raise ApiError(msg, status=r.status_code, body=body)
    if r.status_code == 204 or not r.content:
        return None
    return r.json()


def health() -> dict:
    return _request("GET", "/health")


def login(email: str, password: str) -> dict:
    return _request("POST", "/auth/login", json={"email": email, "password": password})


def register_candidate(email: str, password: str, full_name: str | None) -> dict:
    return _request(
        "POST",
        "/auth/register/candidate",
        json={"email": email, "password": password, "full_name": full_name},
    )


def register_hr(
    email: str,
    password: str,
    full_name: str | None,
    company_name: str,
    contact_phone: str | None,
    company_description: str | None,
) -> dict:
    return _request(
        "POST",
        "/auth/register/hr",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "company_name": company_name,
            "contact_phone": contact_phone,
            "company_description": company_description,
        },
    )


def me() -> dict:
    return _request("GET", "/users/me")


def upload_avatar(file_path: str) -> dict:
    from pathlib import Path

    name = Path(file_path).name
    with open(file_path, "rb") as f:
        files = {"file": (name, f)}
        return _request("POST", "/users/me/avatar", files=files)


def hr_profile() -> dict | None:
    return _request("GET", "/users/me/hr-profile")


def list_jobs_public() -> list:
    return _request("GET", "/candidate/jobs")


def list_my_cvs() -> list:
    return _request("GET", "/candidate/cvs")


def upload_cv(file_path: str) -> dict:
    from pathlib import Path

    name = Path(file_path).name
    with open(file_path, "rb") as f:
        files = {"file": (name, f)}
        return _request("POST", "/candidate/cvs", files=files)


def apply_job(job_id: int, cv_id: int) -> dict:
    return _request("POST", f"/candidate/jobs/{job_id}/apply", json={"cv_id": cv_id})


def hr_dashboard() -> dict:
    return _request("GET", "/hr/dashboard")


def hr_create_job(payload: dict) -> dict:
    return _request("POST", "/hr/jobs", json=payload)


def hr_my_jobs() -> list:
    return _request("GET", "/hr/jobs")


def hr_submit_job(job_id: int) -> dict:
    return _request("PUT", f"/hr/jobs/{job_id}/submit")


def hr_applications() -> list:
    return _request("GET", "/hr/applications")


def admin_dashboard() -> dict:
    return _request("GET", "/admin/dashboard")


def admin_pending_hr() -> list:
    return _request("GET", "/admin/pending/hr")


def admin_approve_hr(user_id: int, note: str | None = None) -> dict:
    return _request("POST", f"/admin/hr/{user_id}/approve", json={"note": note})


def admin_reject_hr(user_id: int, note: str | None = None) -> dict:
    return _request("POST", f"/admin/hr/{user_id}/reject", json={"note": note})


def admin_pending_jobs() -> list:
    return _request("GET", "/admin/pending/jobs")


def admin_approve_job(job_id: int, note: str | None = None) -> dict:
    return _request("POST", f"/admin/jobs/{job_id}/approve", json={"note": note})


def admin_reject_job(job_id: int, note: str | None = None) -> dict:
    return _request("POST", f"/admin/jobs/{job_id}/reject", json={"note": note})


def admin_list_users() -> list:
    return _request("GET", "/admin/users")
