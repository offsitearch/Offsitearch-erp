"""Deterministic Indian name generator using Faker.

All names are generated once with a fixed seed so repeated calls return
the same list.  Use ``generate_names(n)`` to get *n* unique full names
along with gender, phone, and a plausible date-of-joining.
"""

from __future__ import annotations

from datetime import date
from random import Random

from faker import Faker

# Fixed seed ensures the same 100 names every time.
_fake = Faker("en_IN")
_rng = Random(42)

# --- Phone number pool ---------------------------------------------------
# Indian mobile numbers starting with 6-9, 10 digits.
_used_phones: set[str] = set()


def _unique_phone() -> str:
    while True:
        prefix = _rng.choice(["6", "7", "8", "9"])
        digits = "".join(str(_rng.randint(0, 9)) for _ in range(9))
        phone = prefix + digits
        if phone not in _used_phones:
            _used_phones.add(phone)
            return phone


# --- Name generation -----------------------------------------------------

def generate_names(
    n: int = 100,
    *,
    join_start: date = date(2024, 1, 1),
    join_end: date = date(2026, 6, 30),
) -> list[dict]:
    """Return *n* unique employee dicts with name, gender, phone, date_of_joining.

    Names are deduplicated by full-name string.  Gender is inferred from
    the first name using a small built-in list of common Indian female
    names (imperfect but sufficient for test data).
    """
    _female_first = {
        "aisha", "amita", "ananya", "anita", "anjali", "anju", "annu",
        "archana", "ashwini", "bharati", "bhavana", "chhaya", "deepa",
        "deepika", "devika", "durga", "eisha", "gauri", "gita", "hema",
        "indira", "jaya", "jyoti", "kajal", "kamala", "kavita", "kiranti",
        "komal", "leena", "lily", "madhavi", "mala", "mamta", "meena",
        "meera", "mohana", "mona", "mridula", "naina", "neelam", "neha",
        "nisha", "nita", "nutan", "pallavi", "pooja", "poorna", "prachi",
        "priya", "rachna", "radha", "ragini", "raina", "ramya", "rani",
        "ranjana", "rashmi", "reena", "ridhima", "roshni", "sadhana",
        "sangeeta", "sanjana", "sapna", "seema", "shailaja", "shalini",
        "shanti", "shobha", "shriya", "simran", "sonal", "sonia", "sudha",
        "sujata", "sunita", "surekha", "swati", "trupti", "uma", "vandana",
        "varsha", "vasundhara", "veena", "vidya", "vimala", "yamini", "zoya",
    }

    seen: set[str] = set()
    results: list[dict] = []

    while len(results) < n:
        first = _fake.first_name()
        last = _fake.last_name()
        full = f"{first} {last}"
        if full in seen:
            continue
        seen.add(full)

        gender = "female" if first.lower() in _female_first else "male"

        # Spread join dates: ~30% joined 2024, ~40% 2025, ~30% 2026
        year_roll = _rng.random()
        if year_roll < 0.30:
            yr = _rng.choice([2024, 2025])
        elif year_roll < 0.70:
            yr = 2025
        else:
            yr = 2026
        mo = _rng.randint(1, 12)
        max_day = 28  # safe for all months
        dy = _rng.randint(1, max_day)
        join = date(yr, mo, dy)
        if join < join_start:
            join = join_start
        if join > join_end:
            join = join_end

        results.append(
            {
                "name": full,
                "gender": gender,
                "phone": _unique_phone(),
                "date_of_joining": join,
            }
        )

    return results
