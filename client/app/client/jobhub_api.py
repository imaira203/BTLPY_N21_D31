from __future__ import annotations

import logging
import re
from pathlib import Path
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
    token = session_store.get_token()
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _request(method: str, path: str, **kwargs: Any) -> Any:
    url = f"{_base()}{path}"
    timeout = 120 if "files" in kwargs else 60
    try:
        resp = requests.request(method, url, headers=_headers(), timeout=timeout, **kwargs)
    except requests.RequestException as e:
        raise ApiError("Không thể kết nối đến máy chủ API", body=str(e)) from e
    if resp.status_code >= 400:
        logger.debug("HTTP %s %s -> %s", method, url, resp.status_code)
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        msg = str(body)
        if isinstance(body, dict) and "detail" in body:
            detail = body["detail"]
            if isinstance(detail, list):
                parts: list[str] = []
                for item in detail:
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
                msg = "; ".join(parts) if parts else str(detail)
            else:
                msg = str(detail)
        raise ApiError(msg, status=resp.status_code, body=body)
    if resp.status_code == 204 or not resp.content:
        return None
    return resp.json()


def _request_raw(method: str, path: str, **kwargs: Any) -> requests.Response:
    url = f"{_base()}{path}"
    try:
        resp = requests.request(method, url, headers=_headers(), timeout=120, **kwargs)
    except requests.RequestException as e:
        raise ApiError("Không thể kết nối đến máy chủ API", body=str(e)) from e
    if resp.status_code >= 400:
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        msg = str(body["detail"]) if isinstance(body, dict) and "detail" in body else str(body)
        raise ApiError(msg, status=resp.status_code, body=body)
    return resp


def _filename_from_cd(header: str | None) -> str | None:
    if not header:
        return None
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', header)
    return m.group(1) if m else None


def health() -> dict:
    return _request("GET", "/health")


def login(email: str, password: str) -> dict:
    return _request("POST", "/auth/login", json={"email": email, "password": password})


def register_candidate(email: str, password: str, full_name: str | None) -> dict:
    return _request("POST", "/auth/register/candidate", json={"email": email, "password": password, "full_name": full_name})


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
    return _request("PUT", "/users/me/email", json={"new_email": new_email, "current_password": current_password})


def update_my_password(current_password: str, new_password: str) -> dict:
    return _request("PUT", "/users/me/password", json={"current_password": current_password, "new_password": new_password})


def update_my_basic_profile(full_name: str | None = None, email: str | None = None) -> dict:
    return _request("PUT", "/users/me/basic", json={"full_name": full_name, "email": email})


def upload_avatar(file_path: str) -> dict:
    name = Path(file_path).name
    with open(file_path, "rb") as f:
        return _request("POST", "/users/me/avatar", files={"file": (name, f)})


def my_avatar_view() -> tuple[bytes, str | None]:
    r = _request_raw("GET", "/users/me/avatar/view")
    return r.content, _filename_from_cd(r.headers.get("Content-Disposition"))


def hr_profile() -> dict | None:
    return _request("GET", "/users/me/hr-profile")


def my_candidate_profile() -> dict | None:
    return _request("GET", "/users/me/candidate-profile")


def update_my_candidate_profile(payload: dict) -> dict:
    return _request("PUT", "/users/me/candidate-profile", json=payload)


def list_jobs_public() -> list:
    return _request("GET", "/candidate/jobs")


def candidate_track_job_view(job_id: int) -> dict:
    return _request("POST", f"/candidate/jobs/{job_id}/view")


def list_my_cvs() -> list:
    return _request("GET", "/candidate/cvs")


def candidate_download_cv(cv_id: int) -> tuple[bytes, str | None]:
    r = _request_raw("GET", f"/candidate/cvs/{cv_id}/download")
    return r.content, _filename_from_cd(r.headers.get("Content-Disposition"))


def candidate_view_cv(cv_id: int) -> tuple[bytes, str | None]:
    r = _request_raw("GET", f"/candidate/cvs/{cv_id}/view")
    return r.content, _filename_from_cd(r.headers.get("Content-Disposition"))


def candidate_delete_cv(cv_id: int) -> dict:
    return _request("DELETE", f"/candidate/cvs/{cv_id}")


def upload_cv(file_path: str) -> dict:
    name = Path(file_path).name
    with open(file_path, "rb") as f:
        return _request("POST", "/candidate/cvs", files={"file": (name, f)})


def apply_job(job_id: int, cv_id: int) -> dict:
    return _request("POST", f"/candidate/jobs/{job_id}/apply", json={"cv_id": cv_id})


def list_my_applications() -> list:
    return _request("GET", "/candidate/applications")


def candidate_save_job(job_id: int) -> dict:
    return _request("POST", f"/candidate/jobs/{job_id}/save")


def candidate_unsave_job(job_id: int) -> dict:
    return _request("DELETE", f"/candidate/jobs/{job_id}/save")


def candidate_saved_jobs() -> list:
    return _request("GET", "/candidate/jobs/saved")


def hr_dashboard() -> dict:
    return _request("GET", "/hr/dashboard")


def hr_create_job(payload: dict) -> dict:
    return _request("POST", "/hr/jobs", json=payload)


def hr_my_jobs() -> list:
    return _request("GET", "/hr/jobs")


def hr_get_job(job_id: int) -> dict:
    return _request("GET", f"/hr/jobs/{job_id}")


def hr_update_job(job_id: int, payload: dict) -> dict:
    return _request("PUT", f"/hr/jobs/{job_id}", json=payload)


def hr_delete_job(job_id: int) -> dict:
    return _request("DELETE", f"/hr/jobs/{job_id}")


def hr_submit_job(job_id: int) -> dict:
    return _request("PUT", f"/hr/jobs/{job_id}/submit")


def hr_applications() -> list:
    return _request("GET", "/hr/applications")


def hr_update_application_status(application_id: int, new_status: str) -> dict:
    return _request("PUT", f"/hr/applications/{application_id}/status", json={"status": new_status})


def hr_download_application_cv(application_id: int) -> tuple[bytes, str | None]:
    r = _request_raw("GET", f"/hr/applications/{application_id}/cv/download")
    return r.content, _filename_from_cd(r.headers.get("Content-Disposition"))


def hr_view_application_cv(application_id: int) -> tuple[bytes, str | None]:
    r = _request_raw("GET", f"/hr/applications/{application_id}/cv/view")
    return r.content, _filename_from_cd(r.headers.get("Content-Disposition"))


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


def admin_candidate_overview() -> list:
    return _request("GET", "/admin/users/candidates")


def admin_hr_overview() -> list:
    return _request("GET", "/admin/users/hrs")


def admin_all_jobs() -> list:
    return _request("GET", "/admin/jobs")


def admin_delete_job(job_id: int) -> dict:
    return _request("DELETE", f"/admin/jobs/{job_id}")


def admin_get_user(user_id: int) -> dict:
    return _request("GET", f"/admin/users/{user_id}")


def admin_lock_user(user_id: int) -> dict:
    return _request("POST", f"/admin/users/{user_id}/lock")


def admin_unlock_user(user_id: int) -> dict:
    return _request("POST", f"/admin/users/{user_id}/unlock")


def admin_hr_detail(user_id: int) -> dict:
    return _request("GET", f"/admin/hr/{user_id}")


def admin_job_detail(job_id: int) -> dict:
    return _request("GET", f"/admin/jobs/{job_id}")
