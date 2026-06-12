"""Expenses module — claims, mileage, approval workflow, CSV export."""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid, csv, io, os, sys, jwt
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')
from database import db

JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')

router = APIRouter(prefix="/expenses", tags=["Expenses"])

HMRC_MILEAGE_RATE_CAR = 0.45   # first 10,000 miles
HMRC_MILEAGE_RATE_CAR_OVER = 0.25
HMRC_MILEAGE_RATE_BIKE = 0.20

EXPENSE_CATEGORIES = [
    "Travel", "Accommodation", "Meals & Entertainment", "Mileage",
    "Equipment & Supplies", "Training & Development", "Subscriptions",
    "Client Entertainment", "Postage & Courier", "Other",
]


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


class ExpenseClaimCreate(BaseModel):
    title: str
    category: str
    amount: float
    currency: str = "GBP"
    expense_date: str
    description: Optional[str] = None
    receipt_url: Optional[str] = None


class MileageClaimCreate(BaseModel):
    journey_date: str
    from_location: str
    to_location: str
    miles: float
    vehicle_type: str = "car"  # car | bike
    purpose: str
    total_miles_ytd: Optional[float] = 0.0


class ExpenseStatusUpdate(BaseModel):
    status: str  # approved | declined | paid
    note: Optional[str] = None


# ── Categories ──────────────────────────────────────────────────────────────

@router.get("/categories")
async def get_categories(_: CurrentUser = Depends(get_current_user)):
    return {"categories": EXPENSE_CATEGORIES}


# ── Expense Claims ───────────────────────────────────────────────────────────

@router.get("/claims")
async def list_claims(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    """List expense claims. Employees see their own; managers/owners see all."""
    query: dict = {"company_id": user.company_id}
    if user.role == "employee":
        query["employee_id"] = user.user_id
    elif employee_id:
        query["employee_id"] = employee_id
    if status:
        query["status"] = status
    claims = await db.expense_claims.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"claims": claims, "total": len(claims)}


@router.post("/claims")
async def create_claim(body: ExpenseClaimCreate, user: CurrentUser = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    claim = {
        "claim_id": f"exp_{uuid.uuid4().hex[:12]}",
        "company_id": user.company_id,
        "employee_id": user.user_id,
        "employee_name": user.name,
        "employee_email": user.email,
        "title": body.title,
        "category": body.category,
        "amount": round(body.amount, 2),
        "currency": body.currency,
        "expense_date": body.expense_date,
        "description": body.description,
        "receipt_url": body.receipt_url,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    await db.expense_claims.insert_one(claim)
    await _audit(user, "expense_claim_submitted", "expense_claim", claim["claim_id"], {"amount": body.amount, "category": body.category})
    return {k: v for k, v in claim.items() if k != "_id"}


@router.patch("/claims/{claim_id}")
async def update_claim_status(claim_id: str, body: ExpenseStatusUpdate, user: CurrentUser = Depends(get_current_user)):
    if user.role not in ("owner", "admin", "manager"):
        raise HTTPException(status_code=403, detail="Only managers and admins can approve expenses")
    valid = {"approved", "declined", "paid", "revert_pending"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {', '.join(valid)}")
    now = datetime.now(timezone.utc).isoformat()
    new_status = "pending" if body.status == "revert_pending" else body.status
    await db.expense_claims.update_one(
        {"claim_id": claim_id, "company_id": user.company_id},
        {"$set": {
            "status": new_status,
            "reviewed_by": user.user_id,
            "reviewed_by_name": user.name,
            "review_note": body.note,
            "reviewed_at": now,
            "updated_at": now,
        }},
    )
    await _audit(user, f"expense_{new_status}", "expense_claim", claim_id, {"note": body.note})
    return {"claim_id": claim_id, "status": new_status}


@router.delete("/claims/{claim_id}")
async def delete_claim(claim_id: str, user: CurrentUser = Depends(get_current_user)):
    claim = await db.expense_claims.find_one({"claim_id": claim_id, "company_id": user.company_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim["employee_id"] != user.user_id and user.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Cannot delete another employee's claim")
    if claim["status"] not in ("pending",):
        raise HTTPException(status_code=400, detail="Only pending claims can be deleted")
    await db.expense_claims.delete_one({"claim_id": claim_id})
    return {"deleted": True}


# ── Mileage Claims ───────────────────────────────────────────────────────────

@router.get("/mileage")
async def list_mileage(user: CurrentUser = Depends(get_current_user)):
    query: dict = {"company_id": user.company_id}
    if user.role == "employee":
        query["employee_id"] = user.user_id
    claims = await db.mileage_claims.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"claims": claims, "total": len(claims)}


@router.post("/mileage")
async def create_mileage_claim(body: MileageClaimCreate, user: CurrentUser = Depends(get_current_user)):
    # Calculate HMRC rate
    ytd = body.total_miles_ytd or 0.0
    if body.vehicle_type == "bike":
        rate = HMRC_MILEAGE_RATE_BIKE
        amount = round(body.miles * rate, 2)
    else:
        # Car: 45p first 10k, 25p after
        if ytd >= 10000:
            rate = HMRC_MILEAGE_RATE_CAR_OVER
            amount = round(body.miles * rate, 2)
        elif ytd + body.miles > 10000:
            first_band = 10000 - ytd
            second_band = body.miles - first_band
            amount = round(first_band * HMRC_MILEAGE_RATE_CAR + second_band * HMRC_MILEAGE_RATE_CAR_OVER, 2)
            rate = round(amount / body.miles, 4)
        else:
            rate = HMRC_MILEAGE_RATE_CAR
            amount = round(body.miles * rate, 2)

    now = datetime.now(timezone.utc).isoformat()
    claim = {
        "mileage_claim_id": f"mil_{uuid.uuid4().hex[:12]}",
        "company_id": user.company_id,
        "employee_id": user.user_id,
        "employee_name": user.name,
        "journey_date": body.journey_date,
        "from_location": body.from_location,
        "to_location": body.to_location,
        "miles": body.miles,
        "vehicle_type": body.vehicle_type,
        "purpose": body.purpose,
        "rate_ppm": rate,
        "amount": amount,
        "currency": "GBP",
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    await db.mileage_claims.insert_one(claim)
    return {k: v for k, v in claim.items() if k != "_id"}


@router.patch("/mileage/{claim_id}")
async def update_mileage_status(claim_id: str, body: ExpenseStatusUpdate, user: CurrentUser = Depends(get_current_user)):
    if user.role not in ("owner", "admin", "manager"):
        raise HTTPException(status_code=403, detail="Only managers and admins can approve mileage claims")
    now = datetime.now(timezone.utc).isoformat()
    new_status = "pending" if body.status == "revert_pending" else body.status
    await db.mileage_claims.update_one(
        {"mileage_claim_id": claim_id, "company_id": user.company_id},
        {"$set": {"status": new_status, "reviewed_by": user.user_id, "reviewed_at": now, "review_note": body.note, "updated_at": now}},
    )
    return {"mileage_claim_id": claim_id, "status": new_status}


# ── CSV Export ───────────────────────────────────────────────────────────────

@router.get("/export/csv")
async def export_expenses_csv(
    status: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    if user.role not in ("owner", "admin", "manager"):
        raise HTTPException(status_code=403, detail="Export requires manager or admin role")
    query: dict = {"company_id": user.company_id}
    if status:
        query["status"] = status
    claims = await db.expense_claims.find(query, {"_id": 0}).sort("expense_date", -1).to_list(10000)
    mileage = await db.mileage_claims.find({"company_id": user.company_id}, {"_id": 0}).sort("journey_date", -1).to_list(10000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Type", "ID", "Employee", "Date", "Category/Purpose", "Description", "Amount (£)", "Currency", "Status", "Reviewed By", "Reviewed At"])
    for c in claims:
        writer.writerow([
            "Expense", c.get("claim_id"), c.get("employee_name"), c.get("expense_date"),
            c.get("category"), c.get("description", ""), c.get("amount"), c.get("currency", "GBP"),
            c.get("status"), c.get("reviewed_by_name", ""), c.get("reviewed_at", ""),
        ])
    for m in mileage:
        writer.writerow([
            "Mileage", m.get("mileage_claim_id"), m.get("employee_name"), m.get("journey_date"),
            f"{m.get('from_location')} → {m.get('to_location')}", m.get("purpose"),
            m.get("amount"), "GBP", m.get("status"), m.get("reviewed_by", ""), m.get("reviewed_at", ""),
        ])

    output.seek(0)
    filename = f"expenses_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Summary ──────────────────────────────────────────────────────────────────

@router.get("/summary")
async def expense_summary(user: CurrentUser = Depends(get_current_user)):
    query: dict = {"company_id": user.company_id}
    if user.role == "employee":
        query["employee_id"] = user.user_id
    all_claims = await db.expense_claims.find(query, {"_id": 0, "amount": 1, "status": 1}).to_list(10000)
    all_mileage = await db.mileage_claims.find(query, {"_id": 0, "amount": 1, "status": 1, "miles": 1}).to_list(10000)

    def _sum(items, status=None):
        return round(sum(i["amount"] for i in items if (status is None or i.get("status") == status)), 2)

    return {
        "expenses": {
            "total_pending": _sum(all_claims, "pending"),
            "total_approved": _sum(all_claims, "approved"),
            "total_paid": _sum(all_claims, "paid"),
            "count_pending": sum(1 for c in all_claims if c.get("status") == "pending"),
        },
        "mileage": {
            "total_pending": _sum(all_mileage, "pending"),
            "total_approved": _sum(all_mileage, "approved"),
            "total_miles": round(sum(m.get("miles", 0) for m in all_mileage), 1),
        },
    }


async def _audit(user: CurrentUser, action: str, entity_type: str, entity_id: str, details: dict):
    await db.audit_log.insert_one({
        "audit_id": f"aud_{uuid.uuid4().hex[:12]}",
        "company_id": user.company_id,
        "user_id": user.user_id,
        "user_name": user.name,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
