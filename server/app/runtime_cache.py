from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import CandidateProfile, CandidateSubscription, HRProfile, Job, JobStatus, User


@dataclass
class RuntimeCache:
    users_by_id: dict[int, User] = field(default_factory=dict)
    jobs_by_id: dict[int, Job] = field(default_factory=dict)
    published_job_ids: list[int] = field(default_factory=list)
    hr_profile_by_user_id: dict[int, HRProfile] = field(default_factory=dict)
    candidate_profile_by_user_id: dict[int, CandidateProfile] = field(default_factory=dict)
    subscription_by_candidate_id: dict[int, CandidateSubscription] = field(default_factory=dict)

    def load_all(self, db: Session) -> None:
        users = db.scalars(select(User)).all()
        jobs = db.scalars(select(Job)).all()
        profiles = db.scalars(select(HRProfile)).all()
        candidate_profiles = db.scalars(select(CandidateProfile)).all()
        subs = db.scalars(select(CandidateSubscription)).all()

        self.users_by_id = {u.id: u for u in users}
        self.jobs_by_id = {j.id: j for j in jobs}
        self.published_job_ids = [j.id for j in jobs if j.status == JobStatus.published]
        self.hr_profile_by_user_id = {p.user_id: p for p in profiles}
        self.candidate_profile_by_user_id = {p.user_id: p for p in candidate_profiles}
        self.subscription_by_candidate_id = {s.candidate_id: s for s in subs}

    def get_published_jobs(self) -> list[Job]:
        return [self.jobs_by_id[jid] for jid in self.published_job_ids if jid in self.jobs_by_id]

    def upsert_user(self, user: User) -> None:
        self.users_by_id[user.id] = user

    def upsert_job(self, job: Job) -> None:
        self.jobs_by_id[job.id] = job
        if job.status == JobStatus.published:
            if job.id not in self.published_job_ids:
                self.published_job_ids.append(job.id)
        else:
            self.published_job_ids = [jid for jid in self.published_job_ids if jid != job.id]

    def upsert_subscription(self, sub: CandidateSubscription) -> None:
        self.subscription_by_candidate_id[sub.candidate_id] = sub

    def upsert_candidate_profile(self, profile: CandidateProfile) -> None:
        self.candidate_profile_by_user_id[profile.user_id] = profile

    def upsert_hr_profile(self, profile: HRProfile) -> None:
        self.hr_profile_by_user_id[profile.user_id] = profile


runtime_cache = RuntimeCache()
