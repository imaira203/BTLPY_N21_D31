from __future__ import annotations

import logging
import re
from typing import Any

import requests

from .. import session_store
from .. import mock_data
from ..config import get_settings, load_api_base

logger = logging.getLogger("jobhub.client")


def _mock_mode() -> bool:
    return get_settings().use_mock_data


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
            if isinstance(d, list):
                parts: list[str] = []
                for item in d:
                    if isinstance(item, dict):
                        field = item.get("loc")
                        field_name = field[-1] if isinstance(field, list) and field else "field"
                        reason = item.get("msg")
                        if field_name == "email":
                            parts.append("Email không hợp lệ")
                        elif reason:
                            parts.append(f"{field_name}: {reason}")
                    else:
                        parts.append(str(item))
                msg = "; ".join(parts) if parts else str(d)
            else:
                msg = str(d)
        raise ApiError(msg, status=r.status_code, body=body)
    if r.status_code == 204 or not r.content:
        return None
    return r.json()


def _request_raw(method: str, path: str, **kwargs: Any) -> requests.Response:
    url = f"{_base()}{path}"
    headers = _headers()
    r = requests.request(method, url, headers=headers, timeout=120, **kwargs)
    if r.status_code >= 400:
        try:
            body = r.json()
        except Exception:
            body = r.text
        msg = str(body)
        if isinstance(body, dict) and "detail" in body:
            msg = str(body["detail"])
        raise ApiError(msg, status=r.status_code, body=body)
    return r


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


def update_my_email(new_email: str, current_password: str) -> dict:
    return _request(
        "PUT",
        "/users/me/email",
        json={"new_email": new_email, "current_password": current_password},
    )


def update_my_password(current_password: str, new_password: str) -> dict:
    return _request(
        "PUT",
        "/users/me/password",
        json={"current_password": current_password, "new_password": new_password},
    )


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


def candidate_download_cv(cv_id: int) -> tuple[bytes, str | None]:
    if _mock_mode():
        raise ApiError("Mock mode không có file CV thật")
    r = _request_raw("GET", f"/candidate/cvs/{cv_id}/download")
    return r.content, _filename_from_cd(r.headers.get("Content-Disposition"))


def candidate_view_cv(cv_id: int) -> tuple[bytes, str | None]:
    if _mock_mode():
        raise ApiError("Mock mode không có file CV thật")
    r = _request_raw("GET", f"/candidate/cvs/{cv_id}/view")
    return r.content, _filename_from_cd(r.headers.get("Content-Disposition"))


def candidate_delete_cv(cv_id: int) -> dict:
    if _mock_mode():
        return {"ok": True}
    return _request("DELETE", f"/candidate/cvs/{cv_id}")


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


def hr_get_job(job_id: int) -> dict:
    if _mock_mode():
        jobs = [j for j in mock_data.MOCK_HR_JOBS if int(j["id"]) == int(job_id)]
        if jobs:
            return jobs[0]
        raise ApiError("Not found", status=404)
    return _request("GET", f"/hr/jobs/{job_id}")


def hr_update_job(job_id: int, payload: dict) -> dict:
    if _mock_mode():
        return {"id": job_id, **payload}
    return _request("PUT", f"/hr/jobs/{job_id}", json=payload)


def hr_delete_job(job_id: int) -> dict:
    if _mock_mode():
        return {"ok": True}
    return _request("DELETE", f"/hr/jobs/{job_id}")


def hr_submit_job(job_id: int) -> dict:
    if _mock_mode():
        return {"id": job_id, "status": "pending_review"}
    return _request("PUT", f"/hr/jobs/{job_id}/submit")


def hr_applications() -> list:
    if _mock_mode():
        return list(mock_data.MOCK_HR_APPLICATIONS)
    return _request("GET", "/hr/applications")


def _filename_from_cd(header: str | None) -> str | None:
    if not header:
        return None
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', header)
    if not m:
        return None
    return m.group(1)


def hr_download_application_cv(application_id: int) -> tuple[bytes, str | None]:
    if _mock_mode():
        raise ApiError("Mock mode không có file CV thật")
    r = _request_raw("GET", f"/hr/applications/{application_id}/cv/download")
    return r.content, _filename_from_cd(r.headers.get("Content-Disposition"))


def hr_view_application_cv(application_id: int) -> tuple[bytes, str | None]:
    if _mock_mode():
        raise ApiError("Mock mode không có file CV thật")
    r = _request_raw("GET", f"/hr/applications/{application_id}/cv/view")
    return r.content, _filename_from_cd(r.headers.get("Content-Disposition"))


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


def admin_get_user(user_id: int) -> dict:
    if _mock_mode():
        users = [u for u in mock_data.MOCK_ADMIN_USERS if int(u.get("id", 0)) == int(user_id)]
        if users:
            return users[0]
        raise ApiError("User not found", status=404)
    return _request("GET", f"/admin/users/{user_id}")


def admin_lock_user(user_id: int) -> dict:
    if _mock_mode():
        return {"ok": True}
    return _request("POST", f"/admin/users/{user_id}/lock")


def admin_unlock_user(user_id: int) -> dict:
    if _mock_mode():
        return {"ok": True}
    return _request("POST", f"/admin/users/{user_id}/unlock")


def admin_hr_detail(user_id: int) -> dict:
    if _mock_mode():
        return {
            "user_id": user_id,
            "email": "pending.hr@company.com",
            "full_name": "HR Demo",
            "is_active": True,
            "company_name": "Công ty demo",
            "contact_phone": "0900000000",
            "company_description": "Mô tả demo",
            "approval_status": "pending",
            "admin_note": None,
        }
    return _request("GET", f"/admin/hr/{user_id}")


def admin_job_detail(job_id: int) -> dict:
    if _mock_mode():
        rows = [j for j in mock_data.MOCK_PENDING_JOBS if int(j.get("id", 0)) == int(job_id)]
        if rows:
            return rows[0]
        raise ApiError("Job not found", status=404)
    return _request("GET", f"/admin/jobs/{job_id}")
