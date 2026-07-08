"""Mock data resolver for the LeasingAI chatbot.

Loads JSON mock data and resolves tool calls against it, matching the
response shapes from the leasing-mcp Pydantic contracts. Write tools
(schedule_tour, capture_lead, etc.) maintain in-memory state for the
duration of the server process.

Data files use per-property keying where appropriate. Two patterns:
  1. Array-based: {"data": [...]} — each row has a "property_id" field.
  2. Dict-based:  {"data": {"1062921": {...}, "1062922": {...}}} — keyed by property_id.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"

_cache: dict[str, Any] = {}
_next_ids = {"tour": 30100, "lead": 24189000, "applicant": 21101000}
_created_tours: list[dict] = []
_created_leads: list[dict] = []

DEFAULT_PROPERTY_ID = 1062921


def _load(filename: str) -> Any:
    if filename not in _cache:
        path = DATA_DIR / filename
        if path.exists():
            _cache[filename] = json.loads(path.read_text())
        else:
            _cache[filename] = {"data": []}
    return _cache[filename]


def _get_by_property(filename: str, property_id: int | None) -> Any:
    """Load a dict-keyed file and return the section for property_id."""
    raw = _load(filename)
    data = raw.get("data", {})
    if isinstance(data, dict):
        pid_str = str(property_id) if property_id else str(DEFAULT_PROPERTY_ID)
        section = data.get(pid_str) or data.get(str(DEFAULT_PROPERTY_ID))
        return {"data": section} if section else {"data": {}}
    return raw


def _filter_array_by_property(filename: str, property_id: int | None) -> list:
    """Load an array-based file and filter rows by property_id."""
    raw = _load(filename)
    items = raw.get("data", [])
    if not property_id:
        return items
    return [item for item in items if item.get("property_id") == property_id]


def _validation_error(tool: str, field: str, expected: str, got: Any) -> dict:
    return {
        "error": {
            "type": "ValidationError",
            "tool": tool,
            "field": field,
            "expected": expected,
            "got": str(got),
            "fix": f"Pass a valid {field}. {expected}",
        }
    }


def resolve_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Route a tool call to the appropriate mock handler."""
    handler = _HANDLERS.get(tool_name)
    if handler is None:
        return {"error": {"type": "tool_not_registered", "tool": tool_name}}
    return handler(args)


# ─── Property reads ──────────────────────────────────────────────────────

def _list_properties(args: dict) -> dict:
    return _load("properties.json")


def _get_property(args: dict) -> dict:
    pid = args.get("property_id")
    data = _load("properties.json")
    for p in data.get("data", []):
        if p["id"] == pid:
            return {"data": p}
    return _validation_error("get_property", "property_id", "Valid property id", pid)


def _get_property_addresses(args: dict) -> dict:
    return _get_by_property("property_addresses.json", args.get("property_id"))


def _get_property_contact_details(args: dict) -> dict:
    return _get_by_property("property_contact_details.json", args.get("property_id"))


def _get_property_lease_terms(args: dict) -> dict:
    pid = args.get("property_id")
    raw = _load("property_lease_terms.json")
    data = raw.get("data", [])
    if isinstance(data, dict):
        pid_str = str(pid) if pid else str(DEFAULT_PROPERTY_ID)
        return {"data": data.get(pid_str, data.get(str(DEFAULT_PROPERTY_ID), []))}
    return raw


def _get_property_utilities(args: dict) -> dict:
    return _get_by_property("property_utilities.json", args.get("property_id"))


def _get_property_selling_points(args: dict) -> dict:
    return _get_by_property("property_selling_points.json", args.get("property_id"))


def _get_property_hours(args: dict) -> dict:
    return _get_by_property("property_hours.json", args.get("property_id"))


def _get_property_policies(args: dict) -> dict:
    return _get_by_property("property_policies.json", args.get("property_id"))


def _get_specials(args: dict) -> dict:
    pid = args.get("property_id")
    items = _filter_array_by_property("property_specials.json", pid)
    return {"data": items}


def _get_addons(args: dict) -> dict:
    return _get_by_property("addons.json", args.get("property_id"))


def _get_floor_plans(args: dict) -> dict:
    if not args.get("move_in_date"):
        return _validation_error(
            "get_floor_plans", "move_in_date",
            "ISO date YYYY-MM-DD. Ask the prospect for their move-in date.",
            args.get("move_in_date"),
        )
    pid = args.get("property_id")
    items = _filter_array_by_property("floorplans.json", pid)
    return {"data": items}


def _get_floor_plan(args: dict) -> dict:
    fid = args.get("floorplan_id")
    data = _load("floorplans.json")
    for fp in data.get("data", []):
        if fp["floorplan_id"] == fid:
            result = {k: v for k, v in fp.items() if k not in ("units_available", "media")}
            return {"data": result}
    return _validation_error("get_floor_plan", "floorplan_id", "Valid floorplan id", fid)


def _list_available_units(args: dict) -> dict:
    if not args.get("move_in_date"):
        return _validation_error(
            "list_available_units", "move_in_date",
            "ISO date YYYY-MM-DD. Ask the prospect for their move-in date.",
            args.get("move_in_date"),
        )
    pid = args.get("property_id")
    units = _filter_array_by_property("available_units.json", pid)

    beds = args.get("number_of_bedrooms")
    if beds is not None:
        units = [u for u in units if u.get("number_of_bedrooms") == beds]

    baths = args.get("number_of_bathrooms")
    if baths is not None:
        units = [u for u in units if u.get("number_of_bathrooms") == baths]

    fid = args.get("floorplan_id")
    if fid is not None:
        fp_data = _load("floorplans.json")
        fp_name = None
        for fp in fp_data.get("data", []):
            if fp["floorplan_id"] == fid:
                fp_name = fp["floorplan_name"]
                break
        if fp_name:
            units = [u for u in units if u.get("property_floorplan_name") == fp_name]

    return {"data": units}


def _get_unit(args: dict) -> dict:
    uid = args.get("unit_space_id")
    data = _load("available_units.json")
    for u in data.get("data", []):
        if u["unit_space_id"] == uid:
            return {"data": u}
    return _validation_error("get_unit", "unit_space_id", "Valid unit_space_id", uid)


def _get_amenities(args: dict) -> dict:
    return _get_by_property("amenities.json", args.get("property_id"))


def _get_fee_catalog(args: dict) -> dict:
    return _get_by_property("fee_catalog.json", args.get("property_id"))


# ─── Availability ─────────────────────────────────────────────────────────

def _get_unit_matrix(args: dict) -> dict:
    return _load("unit_matrix.json")


# ─── Tours ────────────────────────────────────────────────────────────────

def _list_tour_types(args: dict) -> dict:
    return _get_by_property("property_available_tour_types.json", args.get("property_id"))


def _get_property_available_tour_types(args: dict) -> dict:
    return _get_by_property("property_available_tour_types.json", args.get("property_id"))


def _get_tour_schedule_time_slots(args: dict) -> dict:
    tour_date = args.get("tour_date")
    tour_type = args.get("tour_type", "tour")
    pid = args.get("property_id")
    if not tour_date:
        return _validation_error(
            "get_tour_schedule_time_slots", "tour_date",
            "ISO date YYYY-MM-DD", tour_date,
        )

    data = _load("tour_time_slots.json")
    slots = data.get("data", [])
    filtered = [s for s in slots
                if s.get("date") == tour_date
                and s.get("tour_type") == tour_type
                and (not pid or s.get("property_id") == pid or "property_id" not in s)]
    if not filtered:
        hours = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
                 "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00"]
        generated_slots = []
        for i, h in enumerate(hours):
            end_h = hours[i + 1] if i + 1 < len(hours) else "16:30"
            generated_slots.append({
                "start_time": h,
                "end_time": end_h,
                "available": random.random() > 0.3,
            })
        filtered = [{"date": tour_date, "tour_type": tour_type, "slots": generated_slots}]

    return {"data": filtered}


def _list_tours(args: dict) -> dict:
    base = _load("tours.json")
    all_tours = base.get("data", []) + _created_tours
    return {"data": all_tours}


def _get_tour(args: dict) -> dict:
    tid = args.get("tour_id")
    base = _load("tours.json")
    all_tours = base.get("data", []) + _created_tours
    for t in all_tours:
        if t["id"] == tid:
            return {"data": t}
    return _validation_error("get_tour", "tour_id", "Valid tour_id", tid)


def _schedule_tour(args: dict) -> dict:
    required = ["application_id", "applicant_id", "property_id", "tour_type", "tour_date", "time_slot"]
    for field in required:
        if field not in args:
            return _validation_error("schedule_tour", field, f"{field} is required", "missing")

    tour_id = _next_ids["tour"]
    _next_ids["tour"] += 1

    tour = {
        "id": tour_id,
        "application_id": args["application_id"],
        "applicant_id": args["applicant_id"],
        "property_id": args["property_id"],
        "tour_type": args["tour_type"],
        "tour_date": args["tour_date"],
        "time_slot": args["time_slot"],
        "status": "scheduled",
        "created_at": f"2026-06-05T{int(time.time()) % 86400 // 3600:02d}:{int(time.time()) % 3600 // 60:02d}:00Z",
    }
    _created_tours.append(tour)
    return {"data": tour}


def _reschedule_tour(args: dict) -> dict:
    tid = args.get("tour_id")
    all_tours = _load("tours.json").get("data", []) + _created_tours
    for t in all_tours:
        if t["id"] == tid:
            t["tour_date"] = args.get("new_tour_date", t["tour_date"])
            if "new_time_slot" in args:
                t["time_slot"] = args["new_time_slot"]
            t["status"] = "rescheduled"
            return {"data": t}
    return _validation_error("reschedule_tour", "tour_id", "Valid tour_id", tid)


def _cancel_tour(args: dict) -> dict:
    tid = args.get("tour_id")
    all_tours = _load("tours.json").get("data", []) + _created_tours
    for t in all_tours:
        if t["id"] == tid:
            t["status"] = "cancelled"
            return {"data": t}
    return _validation_error("cancel_tour", "tour_id", "Valid tour_id", tid)


# ─── Leads ────────────────────────────────────────────────────────────────

def _capture_lead(args: dict) -> dict:
    for field in ("property_id", "first_name", "last_name"):
        if not args.get(field):
            return _validation_error("capture_lead", field, f"{field} is required", "missing")

    app_id = _next_ids["lead"]
    _next_ids["lead"] += 1
    applicant_id = _next_ids["applicant"]
    _next_ids["applicant"] += 1

    lead = {
        "id": app_id,
        "primary_applicant": {
            "id": applicant_id,
            "first_name": args["first_name"],
            "last_name": args["last_name"],
            "email": args.get("email"),
            "phone": args.get("phone"),
        },
        "property_id": args["property_id"],
        "status": "prospect",
        "source": "website_chat",
        "move_in_date": args.get("move_in_date"),
        "desired_bedrooms": args.get("desired_bedrooms"),
        "created_at": f"2026-06-05T{int(time.time()) % 86400 // 3600:02d}:{int(time.time()) % 3600 // 60:02d}:00Z",
    }
    _created_leads.append(lead)
    return {"data": lead}


def _search_leads(args: dict) -> dict:
    base = _load("leads.json")
    all_leads = base.get("data", []) + _created_leads
    email = args.get("email", "").lower()
    phone = args.get("phone", "")
    if email or phone:
        filtered = []
        for lead in all_leads:
            pa = lead.get("primary_applicant", {})
            if email and pa.get("email", "").lower() == email:
                filtered.append(lead)
            elif phone and pa.get("phone", "") == phone:
                filtered.append(lead)
        return {"data": filtered}
    return {"data": all_leads}


def _get_lead(args: dict) -> dict:
    aid = args.get("application_id")
    base = _load("leads.json")
    all_leads = base.get("data", []) + _created_leads
    for lead in all_leads:
        if lead["id"] == aid:
            return {"data": lead}
    return _validation_error("get_lead", "application_id", "Valid application_id", aid)


def _list_lead_activities(args: dict) -> dict:
    aid = args.get("application_id")
    base = _load("leads.json")
    all_leads = base.get("data", []) + _created_leads
    for lead in all_leads:
        if lead["id"] == aid:
            return {"data": lead.get("activities", [])}
    return {"data": []}


def _search_applicant(args: dict) -> dict:
    data = _load("applicants.json")
    applicants = data.get("data", [])
    email = args.get("email", "").lower()
    phone = args.get("phone", "")
    if email:
        applicants = [a for a in applicants if a.get("email", "").lower() == email]
    elif phone:
        applicants = [a for a in applicants if a.get("phone", "") == phone]
    return {"data": applicants}


def _update_applicant(args: dict) -> dict:
    aid = args.get("applicant_id")
    return {
        "data": {
            "id": aid,
            "first_name": args.get("first_name", "Updated"),
            "last_name": args.get("last_name", "Applicant"),
            "email": args.get("email"),
            "phone": args.get("phone"),
            "status": "prospect",
            "updated": True,
        }
    }


def _update_guest_card(args: dict) -> dict:
    aid = args.get("application_id")
    return {
        "data": {
            "id": aid,
            "move_in_date": args.get("move_in_date"),
            "desired_bedrooms": args.get("desired_bedrooms"),
            "source": args.get("source", "website_chat"),
            "notes": args.get("notes"),
            "updated": True,
        }
    }


# ─── Platform ─────────────────────────────────────────────────────────────

def _search_tools(args: dict) -> dict:
    from tools import TOOLS
    query = args.get("query", "").lower()
    matches = []
    for t in TOOLS:
        fn = t["function"]
        if query in fn["name"].lower() or query in fn.get("description", "").lower():
            matches.append({"name": fn["name"], "description": fn.get("description", "")[:200]})
    return {"data": matches}


def _ping(args: dict) -> dict:
    return {"ok": True}


def _fetch_auth_token_demo(args: dict) -> dict:
    return {"token": "eyJ***REDACTED***", "expires_in": 3600, "token_type": "Bearer"}


def _echo_request_headers(args: dict) -> dict:
    return {"headers": {"x-client": "demo", "x-request-id": "mock-001", "content-type": "application/json"}}


def _list_skills(args: dict) -> dict:
    return {"data": [{"name": "leasing-assistant", "description": "Property leasing conversation skill"}]}


_HANDLERS: dict[str, Any] = {
    "list_properties": _list_properties,
    "get_property": _get_property,
    "get_property_addresses": _get_property_addresses,
    "get_property_contact_details": _get_property_contact_details,
    "get_property_lease_terms": _get_property_lease_terms,
    "get_property_utilities": _get_property_utilities,
    "get_property_selling_points": _get_property_selling_points,
    "get_property_hours": _get_property_hours,
    "get_property_policies": _get_property_policies,
    "get_specials": _get_specials,
    "get_addons": _get_addons,
    "get_floor_plans": _get_floor_plans,
    "get_floor_plan": _get_floor_plan,
    "list_available_units": _list_available_units,
    "get_unit": _get_unit,
    "get_amenities": _get_amenities,
    "get_fee_catalog": _get_fee_catalog,
    "get_unit_matrix": _get_unit_matrix,
    "list_tour_types": _list_tour_types,
    "get_property_available_tour_types": _get_property_available_tour_types,
    "get_tour_schedule_time_slots": _get_tour_schedule_time_slots,
    "list_tours": _list_tours,
    "get_tour": _get_tour,
    "schedule_tour": _schedule_tour,
    "reschedule_tour": _reschedule_tour,
    "cancel_tour": _cancel_tour,
    "capture_lead": _capture_lead,
    "search_leads": _search_leads,
    "get_lead": _get_lead,
    "list_lead_activities": _list_lead_activities,
    "search_applicant": _search_applicant,
    "update_applicant": _update_applicant,
    "update_guest_card": _update_guest_card,
    "search_tools": _search_tools,
    "ping": _ping,
    "fetch_auth_token_demo": _fetch_auth_token_demo,
    "echo_request_headers": _echo_request_headers,
    "list_skills": _list_skills,
}
