from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import random

from faker import Faker

from utils.corpora import DEPARTMENTS, LOCATIONS
from utils.dates import TimeWindow, iso, now_utc, random_workday_datetime, window_last_days
from utils.ids import gid
from utils.randomness import build_faker, build_rng
from utils.db import bulk_insert, bulk_update


@dataclass(frozen=True)
class User:
    user_id: str
    organization_id: str
    email: str
    full_name: str
    title: str
    department: str
    location: str
    role: str
    manager_user_id: str | None
    hire_date: str
    created_at: str
    deactivated_at: str | None


def _title_for_department(rng: random.Random, dept: str, level: str) -> str:
    if dept == "Engineering":
        return rng.choice(["Software Engineer", "Senior Software Engineer", "Staff Engineer"]) if level == "ic" else rng.choice([
            "Engineering Manager",
            "Senior Engineering Manager",
            "Director of Engineering",
        ])
    if dept == "Product":
        return rng.choice(["Product Manager", "Senior Product Manager"]) if level == "ic" else rng.choice([
            "Group Product Manager",
            "Director of Product",
        ])
    if dept == "Design":
        return rng.choice(["Product Designer", "Senior Product Designer"]) if level == "ic" else rng.choice([
            "Design Manager",
            "Head of Design",
        ])
    if dept == "Marketing":
        return rng.choice(["Marketing Manager", "Growth Marketer", "Content Strategist"]) if level == "ic" else rng.choice([
            "Marketing Director",
            "VP Marketing",
        ])
    if dept == "Sales":
        return rng.choice(["Account Executive", "Sales Development Rep", "Sales Engineer"]) if level == "ic" else rng.choice([
            "Sales Manager",
            "Regional Sales Director",
        ])
    if dept == "Customer Success":
        return rng.choice(["Customer Success Manager", "Solutions Consultant", "Support Specialist"]) if level == "ic" else rng.choice([
            "CS Manager",
            "Director of Customer Success",
        ])
    if dept in {"Operations", "IT", "Security", "People", "Finance", "Legal", "RevOps", "QA", "Data"}:
        base = {
            "Operations": ["Program Manager", "Operations Manager"],
            "IT": ["IT Specialist", "Systems Administrator"],
            "Security": ["Security Analyst", "Security Engineer"],
            "People": ["People Partner", "Recruiter"],
            "Finance": ["Financial Analyst", "Accountant"],
            "Legal": ["Legal Counsel"],
            "RevOps": ["Revenue Analyst", "Sales Operations Specialist"],
            "QA": ["QA Engineer", "Test Engineer"],
            "Data": ["Data Analyst", "Data Scientist"],
        }
        mgr = {
            "Operations": ["Operations Lead", "Director of Operations"],
            "IT": ["IT Manager", "Director of IT"],
            "Security": ["Security Manager", "Head of Security"],
            "People": ["People Manager", "Head of People"],
            "Finance": ["Finance Manager", "Controller"],
            "Legal": ["General Counsel"],
            "RevOps": ["RevOps Manager", "Head of RevOps"],
            "QA": ["QA Manager"],
            "Data": ["Analytics Manager", "Head of Data"],
        }
        return rng.choice(base[dept]) if level == "ic" else rng.choice(mgr[dept])

    return rng.choice(["Specialist", "Manager"]) if level == "ic" else rng.choice(["Director", "VP"])


def _make_unique_email(base_local_part: str, domain: str, used: set[str]) -> str:
    # Enterprise email pattern: first.last(+suffix)@domain
    local = base_local_part
    email = f"{local}@{domain}"
    if email not in used:
        used.add(email)
        return email

    i = 2
    while True:
        email = f"{local}{i}@{domain}"
        if email not in used:
            used.add(email)
            return email
        i += 1


def generate_users(conn, cfg, org, teams) -> list[User]:
    rng = build_rng(cfg.seed + 23)
    fk = build_faker(cfg.seed + 29)
    tw = window_last_days(cfg.history_days, end=now_utc())

    # Approximate enterprise composition.
    dept_weights = {
        "Engineering": 0.28,
        "Product": 0.07,
        "Design": 0.05,
        "QA": 0.05,
        "Data": 0.06,
        "Marketing": 0.12,
        "Sales": 0.14,
        "Customer Success": 0.10,
        "Operations": 0.05,
        "IT": 0.03,
        "Security": 0.02,
        "People": 0.02,
        "Finance": 0.01,
        "Legal": 0.005,
        "RevOps": 0.025,
    }

    depts = list(dept_weights.keys())
    weights = [dept_weights[d] for d in depts]

    users: list[User] = []
    used_emails: set[str] = set()

    # Create executives first (top of org chart).
    exec_titles = ["CEO", "CTO", "CPO", "CMO", "CRO", "COO", "CFO"]
    exec_depts = ["Operations", "Engineering", "Product", "Marketing", "Sales", "Operations", "Finance"]
    exec_ids: list[str] = []
    for title, dept in zip(exec_titles, exec_depts):
        uid = gid()
        full_name = fk.name()
        base_local = full_name.lower().replace(" ", ".")
        email = _make_unique_email(base_local, org.domain, used_emails)
        created_at = random_workday_datetime(rng, tw)
        hire_date = created_at.date() - timedelta(days=rng.randint(365 * 2, 365 * 8))
        u = User(
            user_id=uid,
            organization_id=org.organization_id,
            email=email,
            full_name=full_name,
            title=title,
            department=dept,
            location=rng.choice(LOCATIONS),
            role="executive",
            manager_user_id=None,
            hire_date=iso(hire_date),
            created_at=iso(created_at),
            deactivated_at=None,
        )
        users.append(u)
        exec_ids.append(uid)

    # Generate remaining users.
    for _ in range(cfg.target_users - len(users)):
        dept = rng.choices(depts, weights=weights, k=1)[0]

        # ~11% managers; plus some directors.
        r = rng.random()
        if r < 0.09:
            role = "manager"
            level = "mgr"
        elif r < 0.11:
            role = "director"
            level = "mgr"
        else:
            role = "ic"
            level = "ic"

        full_name = fk.name()
        base_local = full_name.lower().replace(" ", ".")
        email = _make_unique_email(base_local, org.domain, used_emails)

        created_at = random_workday_datetime(rng, tw)
        tenure_years = max(0.1, rng.lognormvariate(0.4, 0.6))
        hire_date = created_at.date() - timedelta(days=int(min(365 * 10, tenure_years * 365)))

        title = _title_for_department(rng, dept, level)

        # Small deactivation rate.
        deactivated_at = None
        if rng.random() < 0.02:
            deact = created_at + timedelta(days=rng.randint(30, cfg.history_days))
            if deact < tw.end:
                deactivated_at = iso(deact)

        manager_user_id = rng.choice(exec_ids)  # temporary, updated below for realism

        u = User(
            user_id=gid(),
            organization_id=org.organization_id,
            email=email,
            full_name=full_name,
            title=title,
            department=dept,
            location=rng.choice(LOCATIONS),
            role=role,
            manager_user_id=manager_user_id,
            hire_date=iso(hire_date),
            created_at=iso(created_at),
            deactivated_at=deactivated_at,
        )
        users.append(u)

    # Improve management chain: pick managers/directors as managers for same department where possible.
    dept_to_managers: dict[str, list[str]] = {}
    for u in users:
        if u.role in {"manager", "director"}:
            dept_to_managers.setdefault(u.department, []).append(u.user_id)

    updates = []
    for u in users:
        if u.role == "executive":
            continue
        mgr_pool = dept_to_managers.get(u.department, [])
        if mgr_pool and rng.random() < 0.80:
            new_mgr = rng.choice(mgr_pool)
        else:
            new_mgr = rng.choice(exec_ids)
        if new_mgr == u.user_id:
            new_mgr = rng.choice(exec_ids)
        updates.append((new_mgr, u.user_id))

    bulk_insert(
        conn,
        "users",
        [
            "user_id",
            "organization_id",
            "email",
            "full_name",
            "title",
            "department",
            "location",
            "role",
            "manager_user_id",
            "hire_date",
            "created_at",
            "deactivated_at",
        ],
        [
            (
                u.user_id,
                u.organization_id,
                u.email,
                u.full_name,
                u.title,
                u.department,
                u.location,
                u.role,
                u.manager_user_id,
                u.hire_date,
                u.created_at,
                u.deactivated_at,
            )
            for u in users
        ],
    )

    bulk_update(conn, "UPDATE users SET manager_user_id = ? WHERE user_id = ?", updates)
    return users
