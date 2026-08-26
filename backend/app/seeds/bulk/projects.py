"""Generate 25 realistic architecture/interior projects for testing.

Pure-Python — no database calls.  ``generate_projects()`` returns dicts
ready for ``db.add_all()`` with all fields matching the Project model.
"""

from __future__ import annotations

from datetime import date
from random import Random

_rng = Random(42)

CLIENTS = [
    {"name": "Rajesh Sharma", "client_type": "individual", "phone": "9823012345", "email": "rajesh.sharma@gmail.com"},
    {"name": "Patil Constructions", "client_type": "developer", "company_name": "Patil Constructions Pvt. Ltd.", "contact_person": "Suresh Patil", "phone": "9823023456", "email": "suresh@patilconstructions.in"},
    {"name": "Kaveri Art Gallery", "client_type": "company", "company_name": "Kaveri Arts", "contact_person": "Ritika Bose", "phone": "9823034567", "email": "ritika@kaveriarts.in"},
    {"name": "Anand Kulkarni", "client_type": "individual", "phone": "9823045678", "email": "anand.k@gmail.com"},
    {"name": "Greenfield Developers", "client_type": "developer", "company_name": "Greenfield Developers LLP", "contact_person": "Prakash Mehta", "phone": "9823056789", "email": "prakash@greenfield.in"},
    {"name": "Nisha Kapoor", "client_type": "individual", "phone": "9823067890", "email": "nisha.kapoor@outlook.com"},
    {"name": "Urban Infra Corp", "client_type": "developer", "company_name": "Urban Infra Corporation", "contact_person": "Vikram Singh", "phone": "9823078901", "email": "vikram@urbaninfra.in"},
    {"name": "Meera Deshpande", "client_type": "individual", "phone": "9823089012", "email": "meera.d@gmail.com"},
]

PROJECTS = [
    {"name": "Sharma Residence - Villa", "project_type": "residential", "category": "Villa", "location": "Kothrud, Pune", "plot_area": 4200, "built_up_area": 6800, "no_of_floors": "G+1", "budget": 21000000, "studio_fee": 1575000, "fee_type": "percent", "fee_percent": 7.5, "status": "in_construction", "priority": "high", "client_idx": 0, "start": "2025-06-01", "end": "2026-12-31"},
    {"name": "Patil Skyline Tower", "project_type": "commercial", "category": "Office Tower", "location": "Baner, Pune", "plot_area": 12000, "built_up_area": 45000, "no_of_floors": "G+12", "budget": 85000000, "studio_fee": 4250000, "fee_type": "percent", "fee_percent": 5.0, "status": "design", "priority": "high", "client_idx": 1, "start": "2025-09-01", "end": "2027-06-30"},
    {"name": "Kaveri Gallery Interiors", "project_type": "interior", "category": "Gallery", "location": "Jangli Maharaj Road, Pune", "plot_area": None, "built_up_area": 3200, "no_of_floors": "1", "budget": 4500000, "studio_fee": 675000, "fee_type": "percent", "fee_percent": 15.0, "status": "in_construction", "priority": "medium", "client_idx": 2, "start": "2025-04-15", "end": "2025-12-31"},
    {"name": "Kulkarni farmhouse", "project_type": "residential", "category": "Farmhouse", "location": "Lonavala", "plot_area": 8000, "built_up_area": 3500, "no_of_floors": "G+1", "budget": 15000000, "studio_fee": 1125000, "fee_type": "percent", "fee_percent": 7.5, "status": "concept", "priority": "medium", "client_idx": 3, "start": "2026-01-15", "end": "2027-03-31"},
    {"name": "Greenfield Enclave Phase 1", "project_type": "residential", "category": "Township", "location": "Hinjewadi, Pune", "plot_area": 45000, "built_up_area": 120000, "no_of_floors": "G+4", "budget": 250000000, "studio_fee": 12500000, "fee_type": "percent", "fee_percent": 5.0, "status": "design", "priority": "high", "client_idx": 4, "start": "2025-10-01", "end": "2028-06-30"},
    {"name": "Kapoor Penthouse", "project_type": "interior", "category": "Penthouse", "location": "Koregaon Park, Pune", "plot_area": None, "built_up_area": 2800, "no_of_floors": "1", "budget": 6000000, "studio_fee": 900000, "fee_type": "percent", "fee_percent": 15.0, "status": "in_construction", "priority": "medium", "client_idx": 5, "start": "2025-07-01", "end": "2026-02-28"},
    {"name": "Urban Tech Park", "project_type": "commercial", "category": "Tech Park", "location": "Magarpatta, Pune", "plot_area": 30000, "built_up_area": 80000, "no_of_floors": "G+8", "budget": 180000000, "studio_fee": 9000000, "fee_type": "percent", "fee_percent": 5.0, "status": "concept", "priority": "high", "client_idx": 6, "start": "2026-03-01", "end": "2028-12-31"},
    {"name": "Deshpande Residence", "project_type": "residential", "category": "Apartment", "location": "Viman Nagar, Pune", "plot_area": None, "built_up_area": 1400, "no_of_floors": "1", "budget": 3500000, "studio_fee": 525000, "fee_type": "percent", "fee_percent": 15.0, "status": "completed", "priority": "low", "client_idx": 7, "start": "2024-06-01", "end": "2025-06-30"},
    {"name": "Wagholi Community Center", "project_type": "institutional", "category": "Community Center", "location": "Wagholi, Pune", "plot_area": 6000, "built_up_area": 4500, "no_of_floors": "G+2", "budget": 12000000, "studio_fee": 900000, "fee_type": "percent", "fee_percent": 7.5, "status": "in_construction", "priority": "medium", "client_idx": 4, "start": "2025-03-01", "end": "2026-03-31"},
    {"name": "Patil Residence Renovation", "project_type": "renovation", "category": "Residential Renovation", "location": "Sadashiv Peth, Pune", "plot_area": None, "built_up_area": 1800, "no_of_floors": "1", "budget": 2500000, "studio_fee": 375000, "fee_type": "percent", "fee_percent": 15.0, "status": "completed", "priority": "low", "client_idx": 1, "start": "2024-09-01", "end": "2025-04-30"},
    {"name": "Greenfield Enclave Phase 2", "project_type": "residential", "category": "Township", "location": "Hinjewadi, Pune", "plot_area": 35000, "built_up_area": 95000, "no_of_floors": "G+4", "budget": 200000000, "studio_fee": 10000000, "fee_type": "percent", "fee_percent": 5.0, "status": "draft", "priority": "medium", "client_idx": 4, "start": "2026-06-01", "end": "2029-06-30"},
    {"name": "Koregaon Park Office", "project_type": "commercial", "category": "Office", "location": "Koregaon Park, Pune", "plot_area": None, "built_up_area": 2200, "no_of_floors": "1", "budget": 3000000, "studio_fee": 450000, "fee_type": "percent", "fee_percent": 15.0, "status": "completed", "priority": "low", "client_idx": 6, "start": "2024-07-01", "end": "2025-03-31"},
    {"name": "Landscape Masterplan - Baner", "project_type": "landscape", "category": "Public Landscape", "location": "Baner, Pune", "plot_area": 15000, "built_up_area": None, "no_of_floors": None, "budget": 8000000, "studio_fee": 600000, "fee_type": "percent", "fee_percent": 7.5, "status": "design", "priority": "medium", "client_idx": 1, "start": "2025-11-01", "end": "2026-08-31"},
    {"name": "Sharma Office Interior", "project_type": "interior", "category": "Office Interior", "location": "Aundh, Pune", "plot_area": None, "built_up_area": 1600, "no_of_floors": "1", "budget": 2200000, "studio_fee": 330000, "fee_type": "percent", "fee_percent": 15.0, "status": "in_construction", "priority": "medium", "client_idx": 0, "start": "2025-08-01", "end": "2026-01-31"},
    {"name": "Mixed-Use Tower Hadapsar", "project_type": "mixed_use", "category": "Mixed-Use", "location": "Hadapsar, Pune", "plot_area": 20000, "built_up_area": 65000, "no_of_floors": "G+15", "budget": 150000000, "studio_fee": 7500000, "fee_type": "percent", "fee_percent": 5.0, "status": "concept", "priority": "high", "client_idx": 6, "start": "2026-04-01", "end": "2029-03-31"},
    {"name": "Kharadi School", "project_type": "institutional", "category": "School", "location": "Kharadi, Pune", "plot_area": 18000, "built_up_area": 12000, "no_of_floors": "G+3", "budget": 45000000, "studio_fee": 3375000, "fee_type": "percent", "fee_percent": 7.5, "status": "design", "priority": "high", "client_idx": 4, "start": "2025-12-01", "end": "2027-06-30"},
    {"name": "Undri Villa Cluster", "project_type": "residential", "category": "Villas", "location": "Undri, Pune", "plot_area": 25000, "built_up_area": 18000, "no_of_floors": "G+1", "budget": 55000000, "studio_fee": 4125000, "fee_type": "percent", "fee_percent": 7.5, "status": "in_construction", "priority": "high", "client_idx": 1, "start": "2025-05-01", "end": "2027-01-31"},
    {"name": "Balewadi High Street Facade", "project_type": "commercial", "category": "Retail Facade", "location": "Balewadi, Pune", "plot_area": None, "built_up_area": 5000, "no_of_floors": "G+3", "budget": 7000000, "studio_fee": 525000, "fee_type": "percent", "fee_percent": 7.5, "status": "completed", "priority": "low", "client_idx": 3, "start": "2024-04-01", "end": "2025-02-28"},
    {"name": "Kasturi Hospitality Hotel", "project_type": "commercial", "category": "Hotel", "location": "Deccan Gymkhana, Pune", "plot_area": 8000, "built_up_area": 22000, "no_of_floors": "G+7", "budget": 95000000, "studio_fee": 4750000, "fee_type": "percent", "fee_percent": 5.0, "status": "under_review", "priority": "high", "client_idx": 3, "start": "2026-02-01", "end": "2028-06-30"},
    {"name": "Navi Mumbai Township", "project_type": "residential", "category": "Township", "location": "Panvel, Navi Mumbai", "plot_area": 60000, "built_up_area": 150000, "no_of_floors": "G+6", "budget": 320000000, "studio_fee": 16000000, "fee_type": "percent", "fee_percent": 5.0, "status": "design", "priority": "high", "client_idx": 6, "start": "2025-11-15", "end": "2029-06-30"},
    {"name": "Mumbai Apartment Revamp", "project_type": "renovation", "category": "Apartment Renovation", "location": "Bandra, Mumbai", "plot_area": None, "built_up_area": 1100, "no_of_floors": "1", "budget": 1800000, "studio_fee": 270000, "fee_type": "percent", "fee_percent": 15.0, "status": "in_construction", "priority": "medium", "client_idx": 5, "start": "2025-10-01", "end": "2026-04-30"},
    {"name": "Mundhwa Corporate Office", "project_type": "commercial", "category": "Corporate HQ", "location": "Mundhwa, Pune", "plot_area": 10000, "built_up_area": 28000, "no_of_floors": "G+5", "budget": 65000000, "studio_fee": 3250000, "fee_type": "percent", "fee_percent": 5.0, "status": "concept", "priority": "medium", "client_idx": 6, "start": "2026-05-01", "end": "2028-01-31"},
    {"name": "Pune University Landscape", "project_type": "landscape", "category": "Campus Landscape", "location": "Savitribai Phule Pune University", "plot_area": 20000, "built_up_area": None, "no_of_floors": None, "budget": 5500000, "studio_fee": 412500, "fee_type": "percent", "fee_percent": 7.5, "status": "in_construction", "priority": "medium", "client_idx": 4, "start": "2025-07-15", "end": "2026-06-30"},
    {"name": "Thane Residential Tower", "project_type": "residential", "category": "High-Rise", "location": "Thane West", "plot_area": 8000, "built_up_area": 35000, "no_of_floors": "G+18", "budget": 120000000, "studio_fee": 6000000, "fee_type": "percent", "fee_percent": 5.0, "status": "draft", "priority": "medium", "client_idx": 1, "start": "2026-07-01", "end": "2029-06-30"},
    {"name": "SP Interior Studio", "project_type": "interior", "category": "Studio", "location": "Salunkhe Vihar, Pune", "plot_area": None, "built_up_area": 900, "no_of_floors": "1", "budget": 1200000, "studio_fee": 180000, "fee_type": "percent", "fee_percent": 15.0, "status": "completed", "priority": "low", "client_idx": 7, "start": "2024-08-01", "end": "2025-01-31"},
]

STATUSES = ["draft", "concept", "design", "under_review", "in_construction", "completed", "on_hold", "cancelled"]


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def generate_projects() -> list[dict]:
    """Return 25 project dicts matching the Project model columns."""
    results = []
    for i, p in enumerate(PROJECTS):
        results.append({
            "project_code": f"OA-{2600 + i // 5:04d}-{p['project_type'][:3].upper()}-{i + 1:02d}",
            "name": p["name"],
            "project_type": p["project_type"],
            "category": p["category"],
            "client_idx": p["client_idx"],
            "location": p["location"],
            "plot_area": p["plot_area"],
            "built_up_area": p["built_up_area"],
            "no_of_floors": p["no_of_floors"],
            "budget": p["budget"],
            "studio_fee": p["studio_fee"],
            "fee_type": p["fee_type"],
            "fee_percent": p["fee_percent"],
            "status": p["status"],
            "priority": p["priority"],
            "start_date": _parse_date(p["start"]),
            "end_date": _parse_date(p["end"]),
        })
    return results
