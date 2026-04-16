from __future__ import annotations

import logging
from typing import Any

import requests

from .. import session_store
from .. import mock_data
from ..config import get_settings, load_api_base

logger = logging.getLogger("jobhub.client")


def _mock_mode() -> bool:
    return get_settings().use_mock_data


def _mock_me() -> dict:
    s = get_settings()
    role = (s.mock_user_role or "candidate").strip().lower()
    if role not in ("candidate", "hr", "admin"):
        role = "candidate"
    return {
        "id": 1,
        "email": "demo@jobhub.local",
        "role": role,
        "full_name": "Người dùng demo",
    }


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
    if _mock_mode():
        return {"status": "ok"}
    return _request("GET", "/health")


def login(email: str, password: str) -> dict:
    if _mock_mode():
        return {"access_token": "mock.access.token"}
    return _request("POST", "/auth/login", json={"email": email, "password": password})


def register_candidate(email: str, password: str, full_name: str | None) -> dict:
    if _mock_mode():
        return {"access_token": "mock.access.token"}
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
    if _mock_mode():
        return {"access_token": "mock.access.token"}
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
    if _mock_mode():
        return _mock_me()
    return _request("GET", "/users/me")


def upload_avatar(file_path: str) -> dict:
    if _mock_mode():
        from pathlib import Path

        return {"avatar_url": f"/mock/{Path(file_path).name}"}
    from pathlib import Path

    name = Path(file_path).name
    with open(file_path, "rb") as f:
        files = {"file": (name, f)}
        return _request("POST", "/users/me/avatar", files=files)


def hr_profile() -> dict | None:
    if _mock_mode():
        return {"approval_status": "approved", "company_name": "Công ty demo"}
    return _request("GET", "/users/me/hr-profile")


def list_jobs_public() -> list:
    if _mock_mode():
        return list(mock_data.MOCK_JOBS)
    return _request("GET", "/candidate/jobs")


def list_my_cvs() -> list:
    if _mock_mode():
        return list(mock_data.MOCK_CVS)
    return _request("GET", "/candidate/cvs")


def upload_cv(file_path: str) -> dict:
    if _mock_mode():
        from pathlib import Path

        name = Path(file_path).name
        return {"id": 99, "original_name": name}
    from pathlib import Path

    name = Path(file_path).name
    with open(file_path, "rb") as f:
        files = {"file": (name, f)}
        return _request("POST", "/candidate/cvs", files=files)


def apply_job(job_id: int, cv_id: int) -> dict:
    if _mock_mode():
        return {"status": "submitted", "job_id": job_id, "cv_id": cv_id}
    return _request("POST", f"/candidate/jobs/{job_id}/apply", json={"cv_id": cv_id})


def hr_dashboard() -> dict:
    if _mock_mode():
        return dict(mock_data.MOCK_HR_DASHBOARD)
    return _request("GET", "/hr/dashboard")


def hr_create_job(payload: dict) -> dict:
    if _mock_mode():
        return {"id": 999, **payload}
    return _request("POST", "/hr/jobs", json=payload)


def hr_my_jobs() -> list:
    if _mock_mode():
        return list(mock_data.MOCK_HR_JOBS)
    return _request("GET", "/hr/jobs")


def hr_submit_job(job_id: int) -> dict:
    if _mock_mode():
        return {"id": job_id, "status": "pending_review"}
    return _request("PUT", f"/hr/jobs/{job_id}/submit")


def hr_applications() -> list:
    if _mock_mode():
        return list(mock_data.MOCK_HR_APPLICATIONS)
    return _request("GET", "/hr/applications")


def admin_dashboard() -> dict:
    if _mock_mode():
        return dict(mock_data.MOCK_ADMIN_DASHBOARD)
    return _request("GET", "/admin/dashboard")


def admin_pending_hr() -> list:
    if _mock_mode():
        return list(mock_data.MOCK_PENDING_HR)
    return _request("GET", "/admin/pending/hr")


def admin_approve_hr(user_id: int, note: str | None = None) -> dict:
    if _mock_mode():
        return {"user_id": user_id, "ok": True}
    return _request("POST", f"/admin/hr/{user_id}/approve", json={"note": note})


def admin_reject_hr(user_id: int, note: str | None = None) -> dict:
    if _mock_mode():
        return {"user_id": user_id, "ok": True}
    return _request("POST", f"/admin/hr/{user_id}/reject", json={"note": note})


def admin_pending_jobs() -> list:
    if _mock_mode():
        return list(mock_data.MOCK_PENDING_JOBS)
    return _request("GET", "/admin/pending/jobs")


def admin_approve_job(job_id: int, note: str | None = None) -> dict:
    if _mock_mode():
        return {"job_id": job_id, "ok": True}
    return _request("POST", f"/admin/jobs/{job_id}/approve", json={"note": note})


def admin_reject_job(job_id: int, note: str | None = None) -> dict:
    if _mock_mode():
        return {"job_id": job_id, "ok": True}
    return _request("POST", f"/admin/jobs/{job_id}/reject", json={"note": note})


def admin_list_users() -> list:
    if _mock_mode():
        return list(mock_data.MOCK_ADMIN_USERS)
    return _request("GET", "/admin/users")
