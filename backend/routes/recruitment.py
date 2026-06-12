"""Recruitment module — jobs, applicants, pipeline stages, templates."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid, os, sys, jwt
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
from database import db

JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')

router = APIRouter(prefix="/recruitment", tags=["Recruitment"])

PIPELINE_STAGES = ["applied", "screening", "interview", "assessment", "offer", "hired", "rejected", "withdrawn"]

OFFER_LETTER_TEMPLATE = """Dear {candidate_name},

We are delighted to offer you the position of {job_title} at {company_name}.

Start Date: {start_date}
Salary: £{salary} per annum
Location: {location}

This offer is subject to satisfactory references and right-to-work verification.

Please confirm your acceptance by signing and returning this letter within 5 working days.

Yours sincerely,
{hiring_manager}
{company_name}"""

JD_TEMPLATE = """Job Title: {job_title}
Department: {department}
Location: {location}
Salary: {salary_range}
Contract Type: {contract_type}

About the Role:
[Describe the role and its purpose]

Key Responsibilities:
• [Responsibility 1]
• [Responsibility 2]
• [Responsibility 3]

Requirements:
• [Required qualification/skill 1]
• [Required qualification/skill 2]

Desirable:
• [Desirable skill 1]

About Us:
[Company description]

How to Apply:
Please send your CV and cover letter to [email]."""

INTERVIEW_HANDBOOK = """Interview Handbook

1. PRE-INTERVIEW CHECKLIST
   □ Review candidate CV and application
   □ Prepare structured questions
   □ Book interview room / set up video call
   □ Send confirmation to candidate
   □ Prepare scoring sheet

2. STRUCTURED INTERVIEW QUESTIONS
   Competency-based questions (STAR method):
   • Tell me about a time you dealt with a difficult colleague
   • Describe a situation where you had to meet a tight deadline
   • Give an example of when you showed initiative

3. LEGAL REMINDERS — DO NOT ASK:
   ✗ Age, date of birth
   ✗ Nationality (only ask right to work in UK)
   ✗ Health conditions or disabilities
   ✗ Pregnancy or family plans
   ✗ Religion, sexual orientation

4. SCORING GUIDE
   1 = No evidence | 2 = Some evidence | 3 = Clear evidence | 4 = Strong evidence | 5 = Exceptional

5. POST-INTERVIEW
   □ Complete scoring sheet immediately
   □ Document decision with justification
   □ Retain records for 6 months (GDPR)
   □ Notify all candidates of outcome"""


class CurrentUser(BaseModel):
    user_id: str
    email: str
    name: str
    role: str = "employee"
    company_id: Optional[str] = None


async def get_current_user(request: Request) -> CurrentUser:
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if session:
        user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    else:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            user_doc = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return CurrentUser(**{k: v for k, v in user_doc.items() if k in CurrentUser.model_fields})


async def require_manager(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role not in ("owner", "admin", "manager"):
        raise HTTPException(status_code=403, detail="Manager or admin role required")
    return user


class JobCreate(BaseModel):
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    contract_type: str = "full_time"
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    closing_date: Optional[str] = None
    hiring_manager_id: Optional[str] = None


class JobUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    contract_type: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    closing_date: Optional[str] = None
    status: Optional[str] = None  # open | filled | closed | draft


class ApplicantCreate(BaseModel):
    job_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    cv_url: Optional[str] = None
    cover_letter: Optional[str] = None
    source: str = "direct"  # direct | linkedin | indeed | referral | agency | other


class ApplicantUpdate(BaseModel):
    stage: Optional[str] = None
    rating: Optional[int] = None   # 1-5
    notes: Optional[str] = None
    interview_date: Optional[str] = None
    offer_salary: Optional[float] = None
    rejection_reason: Optional[str] = None


# ── Jobs ─────────────────────────────────────────────────────────────────────

@router.get("/jobs")
async def list_jobs(status: Optional[str] = None, user: CurrentUser = Depends(get_current_user)):
    query: dict = {"company_id": user.company_id}
    if status:
        query["status"] = status
    jobs = await db.recruitment_jobs.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    for j in jobs:
        j["applicant_count"] = await db.recruitment_applicants.count_documents({"job_id": j["job_id"]})
    return {"jobs": jobs, "total": len(jobs)}


@router.get("/jobs/stats")
async def job_stats(user: CurrentUser = Depends(get_current_user)):
    total = await db.recruitment_jobs.count_documents({"company_id": user.company_id})
    open_ = await db.recruitment_jobs.count_documents({"company_id": user.company_id, "status": "open"})
    filled = await db.recruitment_jobs.count_documents({"company_id": user.company_id, "status": "filled"})
    total_applicants = await db.recruitment_applicants.count_documents({"company_id": user.company_id})
    hired = await db.recruitment_applicants.count_documents({"company_id": user.company_id, "stage": "hired"})
    return {"total_jobs": total, "open_jobs": open_, "filled_jobs": filled, "total_applicants": total_applicants, "hired": hired}


@router.post("/jobs")
async def create_job(body: JobCreate, user: CurrentUser = Depends(require_manager)):
    now = datetime.now(timezone.utc).isoformat()
    job = {
        "job_id": f"job_{uuid.uuid4().hex[:12]}",
        "company_id": user.company_id,
        "title": body.title,
        "department": body.department,
        "location": body.location,
        "contract_type": body.contract_type,
        "salary_min": body.salary_min,
        "salary_max": body.salary_max,
        "description": body.description,
        "requirements": body.requirements,
        "closing_date": body.closing_date,
        "hiring_manager_id": body.hiring_manager_id or user.user_id,
        "hiring_manager_name": user.name,
        "status": "open",
        "created_by": user.user_id,
        "created_at": now,
        "updated_at": now,
    }
    await db.recruitment_jobs.insert_one(job)
    return {k: v for k, v in job.items() if k != "_id"}


@router.patch("/jobs/{job_id}")
async def update_job(job_id: str, body: JobUpdate, user: CurrentUser = Depends(require_manager)):
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.recruitment_jobs.update_one(
        {"job_id": job_id, "company_id": user.company_id},
        {"$set": updates},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, **updates}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, user: CurrentUser = Depends(require_manager)):
    await db.recruitment_jobs.delete_one({"job_id": job_id, "company_id": user.company_id})
    await db.recruitment_applicants.delete_many({"job_id": job_id})
    return {"deleted": True}


# ── Applicants ───────────────────────────────────────────────────────────────

@router.get("/applicants")
async def list_applicants(
    job_id: Optional[str] = None,
    stage: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    query: dict = {"company_id": user.company_id}
    if job_id:
        query["job_id"] = job_id
    if stage:
        query["stage"] = stage
    applicants = await db.recruitment_applicants.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {"applicants": applicants, "total": len(applicants)}


@router.post("/applicants")
async def add_applicant(body: ApplicantCreate, user: CurrentUser = Depends(require_manager)):
    job = await db.recruitment_jobs.find_one({"job_id": body.job_id, "company_id": user.company_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    now = datetime.now(timezone.utc).isoformat()
    applicant = {
        "applicant_id": f"app_{uuid.uuid4().hex[:12]}",
        "company_id": user.company_id,
        "job_id": body.job_id,
        "job_title": job.get("title"),
        "first_name": body.first_name,
        "last_name": body.last_name,
        "full_name": f"{body.first_name} {body.last_name}",
        "email": body.email,
        "phone": body.phone,
        "cv_url": body.cv_url,
        "cover_letter": body.cover_letter,
        "source": body.source,
        "stage": "applied",
        "rating": None,
        "notes": None,
        "interview_date": None,
        "offer_salary": None,
        "rejection_reason": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.recruitment_applicants.insert_one(applicant)
    return {k: v for k, v in applicant.items() if k != "_id"}


@router.patch("/applicants/{applicant_id}")
async def update_applicant(applicant_id: str, body: ApplicantUpdate, user: CurrentUser = Depends(require_manager)):
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if "stage" in updates and updates["stage"] not in PIPELINE_STAGES:
        raise HTTPException(status_code=400, detail=f"Stage must be one of: {', '.join(PIPELINE_STAGES)}")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.recruitment_applicants.update_one(
        {"applicant_id": applicant_id, "company_id": user.company_id},
        {"$set": updates},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Applicant not found")
    # If hired, update job status to filled
    if updates.get("stage") == "hired":
        appl = await db.recruitment_applicants.find_one({"applicant_id": applicant_id}, {"_id": 0, "job_id": 1})
        if appl:
            await db.recruitment_jobs.update_one({"job_id": appl["job_id"]}, {"$set": {"status": "filled"}})
    return {"applicant_id": applicant_id, **updates}


@router.delete("/applicants/{applicant_id}")
async def delete_applicant(applicant_id: str, user: CurrentUser = Depends(require_manager)):
    await db.recruitment_applicants.delete_one({"applicant_id": applicant_id, "company_id": user.company_id})
    return {"deleted": True}


# ── Pipeline stage list ───────────────────────────────────────────────────────

@router.get("/pipeline-stages")
async def get_pipeline_stages(_: CurrentUser = Depends(get_current_user)):
    return {"stages": PIPELINE_STAGES}


# ── Templates ────────────────────────────────────────────────────────────────

@router.get("/templates/offer-letter")
async def get_offer_letter_template(
    candidate_name: str = "Candidate Name",
    job_title: str = "Job Title",
    company_name: str = "Company Name",
    start_date: str = "TBD",
    salary: str = "XX,XXX",
    location: str = "Office",
    hiring_manager: str = "HR Manager",
    _: CurrentUser = Depends(get_current_user),
):
    return {
        "template": OFFER_LETTER_TEMPLATE.format(
            candidate_name=candidate_name,
            job_title=job_title,
            company_name=company_name,
            start_date=start_date,
            salary=salary,
            location=location,
            hiring_manager=hiring_manager,
        )
    }


@router.get("/templates/job-description")
async def get_jd_template(
    job_title: str = "Job Title",
    department: str = "Department",
    location: str = "Location",
    salary_range: str = "Competitive",
    contract_type: str = "Permanent, Full-time",
    _: CurrentUser = Depends(get_current_user),
):
    return {
        "template": JD_TEMPLATE.format(
            job_title=job_title,
            department=department,
            location=location,
            salary_range=salary_range,
            contract_type=contract_type,
        )
    }


@router.get("/templates/interview-handbook")
async def get_interview_handbook(_: CurrentUser = Depends(get_current_user)):
    return {"handbook": INTERVIEW_HANDBOOK}
