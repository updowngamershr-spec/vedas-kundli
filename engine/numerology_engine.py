# -*- coding: utf-8 -*-
"""
Vedas Kundli - Comprehensive Numerology Engine
Supports independent Pythagorean and Chaldean calculation systems,
Core Numbers (Birth, Life Path, Expression, Soul Urge, Personality),
Lo Shu Grid (3x3 planes of expression, missing & repeated numbers),
Pinnacles & Challenges, Personal Year/Month/Day cycles,
Indian language transliteration (Hindi Devanagari & Punjabi Gurmukhi),
and source-traceable, grounded remedy frameworks.
"""

from __future__ import annotations
import os
import sys
import re
import json
import calendar
from collections import Counter
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# 1. KNOWLEDGE BASE LOADING & PATH RESOLUTION
# ---------------------------------------------------------------------------

def get_knowledge_base_path() -> str:
    """Resolve the location of numerology_knowledge_base.json supporting frozen mode."""
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidate_paths = [
        os.path.join(base_dir, "data", "numerology_knowledge_base.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "numerology_knowledge_base.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "numerology_knowledge_base.json"),
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            return os.path.abspath(p)
    return candidate_paths[0]

_KB_CACHE: Optional[Dict[str, Any]] = None

def load_knowledge_base() -> Dict[str, Any]:
    global _KB_CACHE
    if _KB_CACHE is not None:
        return _KB_CACHE
    path = get_knowledge_base_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                _KB_CACHE = json.load(f)
                return _KB_CACHE
        except Exception:
            pass
    # Fallback to built-in baseline if file read fails
    _KB_CACHE = {
        "version": "1.1.0",
        "product": "Vedas Kundli Numerology",
        "number_themes": {str(i): {"en": f"Theme for {i}", "hi": f"अंक {i} का विषय"} for i in range(1, 10)},
        "remedies": []
    }
    return _KB_CACHE


# ---------------------------------------------------------------------------
# 2. NUMEROLOGY LETTER CHARTS (STRICTLY SEPARATED)
# ---------------------------------------------------------------------------

# Western / Pythagorean System (1 to 9)
PYTHAGOREAN_TABLE: Dict[str, int] = {
    'A': 1, 'J': 1, 'S': 1,
    'B': 2, 'K': 2, 'T': 2,
    'C': 3, 'L': 3, 'U': 3,
    'D': 4, 'M': 4, 'V': 4,
    'E': 5, 'N': 5, 'W': 5,
    'F': 6, 'O': 6, 'X': 6,
    'G': 7, 'P': 7, 'Y': 7,
    'H': 8, 'Q': 8, 'Z': 8,
    'I': 9, 'R': 9,
}

# Ancient Chaldean System (1 to 8; 9 is sacred and never assigned to a letter)
CHALDEAN_TABLE: Dict[str, int] = {
    'A': 1, 'I': 1, 'J': 1, 'Q': 1, 'Y': 1,
    'B': 2, 'K': 2, 'R': 2,
    'C': 3, 'G': 3, 'L': 3, 'S': 3,
    'D': 4, 'M': 4, 'T': 4,
    'E': 5, 'H': 5, 'N': 5, 'X': 5,
    'U': 6, 'V': 6, 'W': 6,
    'O': 7, 'Z': 7,
    'F': 8, 'P': 8,
}

MASTER_NUMBERS: Set[int] = {11, 22, 33}


# ---------------------------------------------------------------------------
# 3. REDUCTION & TRACE ALGORITHMS
# ---------------------------------------------------------------------------

def digit_sum(n: int) -> int:
    """Sum individual decimal digits of an integer."""
    return sum(int(ch) for ch in str(abs(int(n))))

def reduce_number(n: int, preserve_masters: bool = True) -> int:
    """
    Numerologically reduce an integer to a single digit (1..9),
    optionally preserving master numbers (11, 22, 33).
    """
    n = abs(int(n))
    while n > 9:
        if preserve_masters and n in MASTER_NUMBERS:
            return n
        n = digit_sum(n)
    return n

def number_trace(n: int, preserve_masters: bool = True) -> Dict[str, Any]:
    """
    Provide step-by-step reduction trace for complete calculation transparency.
    """
    original = int(n)
    steps = [original]
    current = abs(original)
    while current > 9:
        if preserve_masters and current in MASTER_NUMBERS:
            break
        current = digit_sum(current)
        steps.append(current)
    return {
        "original": original,
        "steps": steps,
        "result": current,
        "is_master": current in MASTER_NUMBERS,
    }


# ---------------------------------------------------------------------------
# 4. INDIC SCRIPT DETECTION & TRANSLITERATION ENGINE
# ---------------------------------------------------------------------------

# Devanagari character mapping table
DEVANAGARI_MAP = {
    'अ': 'A', 'आ': 'AA', 'इ': 'I', 'ई': 'EE', 'उ': 'U', 'ऊ': 'OO',
    'ऋ': 'RI', 'ए': 'E', 'ऐ': 'AI', 'ओ': 'O', 'औ': 'AU',
    'क': 'K', 'ख': 'KH', 'ग': 'G', 'घ': 'GH', 'ङ': 'NG',
    'च': 'CH', 'छ': 'CHH', 'ज': 'J', 'झ': 'JH', 'ञ': 'NY',
    'ट': 'T', 'ठ': 'TH', 'ड': 'D', 'ढ': 'DH', 'ण': 'N',
    'त': 'T', 'थ': 'TH', 'द': 'D', 'ध': 'DH', 'न': 'N',
    'प': 'P', 'फ': 'PH', 'ब': 'B', 'भ': 'BH', 'म': 'M',
    'य': 'Y', 'र': 'R', 'ल': 'L', 'व': 'V', 'श': 'SH',
    'ष': 'SH', 'स': 'S', 'ह': 'H', 'क्ष': 'KSH', 'त्र': 'TR', 'ज्ञ': 'GYA',
    # Matras
    'ा': 'A', 'ि': 'I', 'ी': 'EE', 'ु': 'U', 'ू': 'OO', 'ृ': 'RI',
    'े': 'E', 'ै': 'AI', 'ो': 'O', 'ौ': 'AU', 'ं': 'N', 'ँ': 'N', 'ः': 'H',
    '्': '' # Virama
}

# Gurmukhi character mapping table
GURMUKHI_MAP = {
    'ਅ': 'A', 'ਆ': 'AA', 'ਇ': 'I', 'ਈ': 'EE', 'ਉ': 'U', 'ਊ': 'OO',
    'ਏ': 'E', 'ਐ': 'AI', 'ਓ': 'O', 'ਔ': 'AU',
    'ਕ': 'K', 'ਖ': 'KH', 'ਗ': 'G', 'ਘ': 'GH', 'ਙ': 'NG',
    'ਚ': 'CH', 'ਛ': 'CHH', 'ਜ': 'J', 'ਝ': 'JH', 'ਞ': 'NY',
    'ਟ': 'T', 'ਠ': 'TH', 'ਡ': 'D', 'ਢ': 'DH', 'ਣ': 'N',
    'ਤ': 'T', 'ਥ': 'TH', 'ਦ': 'D', 'ਧ': 'DH', 'ਨ': 'N',
    'ਪ': 'P', 'ਫ': 'PH', 'ਬ': 'B', 'ਭ': 'BH', 'ਮ': 'M',
    'ਯ': 'Y', 'ਰ': 'R', 'ਲ': 'L', 'ਵ': 'V', 'ੜ': 'R',
    'ਸ': 'S', 'ਹ': 'H', 'ਸ਼': 'SH', 'ਖ਼': 'KH', 'ਗ਼': 'G', 'ਜ਼': 'Z', 'ਫ਼': 'F',
    # Matras
    'ਾ': 'A', 'ਿ': 'I', 'ੀ': 'EE', 'ੁ': 'U', 'ੂ': 'OO',
    'ੇ': 'E', 'ੈ': 'AI', 'ੋ': 'O', 'ੌ': 'AU', 'ਂ': 'N', 'ੰ': 'N', '੍': ''
}

def detect_script(text: str) -> str:
    """Identify if the text is Latin, Devanagari (Hindi), Gurmukhi (Punjabi), or Mixed."""
    has_devanagari = any('\u0900' <= ch <= '\u097F' for ch in text)
    has_gurmukhi = any('\u0A00' <= ch <= '\u0A7F' for ch in text)
    has_latin = any(('A' <= ch <= 'Z') or ('a' <= ch <= 'z') for ch in text)
    if has_devanagari and not has_gurmukhi and not has_latin:
        return "Devanagari"
    if has_gurmukhi and not has_devanagari and not has_latin:
        return "Gurmukhi"
    if has_latin and not has_devanagari and not has_gurmukhi:
        return "Latin"
    if has_devanagari or has_gurmukhi:
        return "Mixed_Indic"
    return "Unknown"

def transliterate_indic_name(name: str) -> Dict[str, Any]:
    """
    Transliterate an Indic name (Devanagari or Gurmukhi) into proposed Latin letters.
    Requires user confirmation because different English spellings yield different numerology totals.
    """
    raw = name.strip()
    script = detect_script(raw)
    
    if script == "Latin":
        clean = re.sub(r"[^A-Za-z]", "", raw).upper()
        return {
            "original_name": raw,
            "script": "Latin",
            "proposed_latin": clean,
            "requires_confirmation": False,
            "transliteration_status": "direct_latin"
        }
    
    proposed = []
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch in DEVANAGARI_MAP:
            proposed.append(DEVANAGARI_MAP[ch])
        elif ch in GURMUKHI_MAP:
            proposed.append(GURMUKHI_MAP[ch])
        elif ch.isascii() and ch.isalpha():
            proposed.append(ch.upper())
        elif ch == ' ':
            proposed.append(' ')
        i += 1

    proposed_str = "".join(proposed).strip()
    proposed_clean = re.sub(r"[^A-Za-z ]", "", proposed_str)
    # normalize spaces
    proposed_clean = " ".join(proposed_clean.split())
    
    return {
        "original_name": raw,
        "script": script,
        "proposed_latin": proposed_clean,
        "requires_confirmation": True,
        "transliteration_status": "confirmation_recommended",
        "method_note": "Different English spellings (e.g., Sharma vs Sarma) alter name numbers. Please confirm the exact Latin spelling."
    }

def clean_name(name: str) -> str:
    """Normalize a Latin name. Raises ValueError if non-Latin characters are present."""
    raw = name or ""
    if any(ch.isalpha() and not ch.isascii() for ch in raw):
        raise ValueError("Indic/non-Latin name requires a user-confirmed Latin transliteration")
    letters = re.sub(r"[^A-Za-z]", "", raw).upper()
    if not letters:
        raise ValueError("Name must contain at least one A-Z letter")
    return letters


# ---------------------------------------------------------------------------
# 5. NAME NUMEROLOGY (PYTHAGOREAN & CHALDEAN)
# ---------------------------------------------------------------------------

def calculate_name_total(name: str, table: Dict[str, int]) -> Dict[str, Any]:
    """Calculate the total and trace of all letters in a name."""
    letters = clean_name(name)
    values = [{"letter": c, "value": table[c]} for c in letters if c in table]
    total = sum(x["value"] for x in values)
    return {
        "normalized_name": letters,
        "letter_values": values,
        "total": total,
        "trace": number_trace(total),
    }

def calculate_name_components(name: str, table: Dict[str, int], y_is_vowel: bool = False) -> Dict[str, Any]:
    """
    Calculate Soul Urge (Vowels), Personality (Consonants), and Expression (Full Name).
    """
    letters = clean_name(name)
    vowels = set("AEIOU")
    if y_is_vowel:
        vowels.add("Y")

    vowel_letters = [c for c in letters if c in vowels and c in table]
    consonant_letters = [c for c in letters if c not in vowels and c in table]

    vowel_total = sum(table[c] for c in vowel_letters)
    consonant_total = sum(table[c] for c in consonant_letters)
    full_total = sum(table[c] for c in letters if c in table)

    return {
        "normalized_name": letters,
        "soul_urge": {
            "letters": vowel_letters,
            "values": [{"letter": c, "value": table[c]} for c in vowel_letters],
            "total": vowel_total,
            "trace": number_trace(vowel_total),
        },
        "personality": {
            "letters": consonant_letters,
            "values": [{"letter": c, "value": table[c]} for c in consonant_letters],
            "total": consonant_total,
            "trace": number_trace(consonant_total),
        },
        "expression": {
            "letters": list(letters),
            "values": [{"letter": c, "value": table[c]} for c in letters if c in table],
            "total": full_total,
            "trace": number_trace(full_total),
        },
        "vowel_policy": "A/E/I/O/U" + (" plus Y" if y_is_vowel else ""),
    }

def calculate_name_karmic_profile(name: str, table: Dict[str, int]) -> Dict[str, Any]:
    """
    Name letter distribution:
    - Missing digits (1..9) = Karmic Lessons
    - Highest frequency digits = Hidden Passion
    """
    letters = clean_name(name)
    counts = Counter(table[c] for c in letters if c in table)
    missing = [n for n in range(1, 10) if counts[n] == 0]
    max_freq = max(counts.values()) if counts else 0
    hidden_passion = [n for n in range(1, 10) if counts[n] == max_freq] if max_freq > 0 else []

    return {
        "letter_number_counts": {str(n): counts[n] for n in range(1, 10)},
        "karmic_lesson_numbers": missing,
        "hidden_passion_numbers": hidden_passion,
        "maximum_frequency": max_freq,
        "method_note": "Derived from letter frequency distribution in the chosen alphabet table."
    }


# ---------------------------------------------------------------------------
# 6. BIRTH & LIFE PATH NUMBERS
# ---------------------------------------------------------------------------

def calculate_birth_number(day: int, preserve_masters: bool = True) -> Dict[str, Any]:
    """
    Calculate Birth Number (Day Number / Moolank / Janmank).
    Represents core identity and primary vibration.
    """
    if not (1 <= int(day) <= 31):
        raise ValueError("Birth day must be between 1 and 31")
    return number_trace(day, preserve_masters=preserve_masters)

def calculate_life_path(year: int, month: int, day: int, policy: str = "component_reduction") -> Dict[str, Any]:
    """
    Calculate Life Path Number (Destiny / Bhagyank).
    Exposes two classical policies:
    1. component_reduction: Reduce Month, Day, and Year separately, then sum.
    2. all_digits: Sum all 8 digits of YYYYMMDD directly.
    """
    if not (1 <= month <= 12):
        raise ValueError("Month must be 1..12")
    max_days = calendar.monthrange(year, month)[1]
    if not (1 <= day <= max_days):
        raise ValueError(f"Invalid date: {year}-{month:02d}-{day:02d} has maximum {max_days} days")

    if policy == "component_reduction":
        m = reduce_number(month, False)
        d = reduce_number(day, False)
        y = reduce_number(digit_sum(year), False)
        total = m + d + y
        return {
            "policy": "component_reduction",
            "month_reduced": m,
            "day_reduced": d,
            "year_reduced": y,
            "sum": total,
            "trace": number_trace(total),
        }
    elif policy == "all_digits":
        raw = f"{year:04d}{month:02d}{day:02d}"
        total = sum(int(ch) for ch in raw)
        return {
            "policy": "all_digits",
            "digits": raw,
            "sum": total,
            "trace": number_trace(total),
        }
    else:
        raise ValueError(f"Unknown Life Path policy: {policy}")


# ---------------------------------------------------------------------------
# 7. CYCLES: PERSONAL YEAR, MONTH, DAY & LIFE CYCLES
# ---------------------------------------------------------------------------

def calculate_personal_year(day: int, month: int, target_year: int) -> Dict[str, Any]:
    """Calculate Personal Year for a given calendar target year."""
    if not (1 <= int(month) <= 12):
        raise ValueError("Month must be 1..12")
    if not (1 <= int(day) <= 31):
        raise ValueError("Day must be 1..31")
    d_red = reduce_number(day, False)
    m_red = reduce_number(month, False)
    y_sum = digit_sum(target_year)
    total = d_red + m_red + y_sum
    return {
        "target_year": int(target_year),
        "day_component": d_red,
        "month_component": m_red,
        "year_component": y_sum,
        "sum": total,
        "trace": number_trace(total),
    }

def calculate_personal_month(personal_year_number: int, month: int) -> Dict[str, Any]:
    """Calculate Personal Month."""
    if not (1 <= month <= 12):
        raise ValueError("Month must be 1..12")
    total = reduce_number(personal_year_number, False) + reduce_number(month, False)
    return {
        "month": month,
        "sum": total,
        "trace": number_trace(total),
    }

def calculate_personal_day(personal_month_number: int, day: int) -> Dict[str, Any]:
    """Calculate Personal Day."""
    if not (1 <= day <= 31):
        raise ValueError("Day must be 1..31")
    total = reduce_number(personal_month_number, False) + reduce_number(day, False)
    return {
        "day": day,
        "sum": total,
        "trace": number_trace(total),
    }

def calculate_life_cycles(month: int, day: int, year: int) -> Dict[str, Any]:
    """Calculate the 3 primary life cycle numbers (Youth, Maturity, Later Years)."""
    m = reduce_number(month, False)
    d = reduce_number(day, False)
    y = reduce_number(digit_sum(year), False)
    return {
        "first_cycle": number_trace(m),
        "second_cycle": number_trace(d),
        "third_cycle": number_trace(y),
        "formula_note": "First cycle corresponds to birth month; second to birth day; third to birth year."
    }


# ---------------------------------------------------------------------------
# 8. PINNACLES & CHALLENGES
# ---------------------------------------------------------------------------

def calculate_pinnacles_and_challenges(day: int, month: int, year: int) -> Dict[str, Any]:
    """
    Calculate the 4 Pinnacles and 4 Challenges based on classical reduction rules.
    """
    m = reduce_number(month, False)
    d = reduce_number(day, False)
    y = reduce_number(digit_sum(year), False)

    # 4 Pinnacles
    p1 = reduce_number(m + d)
    p2 = reduce_number(d + y)
    p3 = reduce_number(p1 + p2)
    p4 = reduce_number(m + y)

    # 4 Challenges
    c1 = abs(d - m)
    c2 = abs(d - y)
    c3 = abs(c1 - c2)
    c4 = abs(m - y)

    return {
        "pinnacles": [p1, p2, p3, p4],
        "challenges": [c1, c2, c3, c4],
        "components": {"month": m, "day": d, "year": y},
        "formula_note": "P1=Month+Day, P2=Day+Year, P3=P1+P2, P4=Month+Year. C1=|Day-Month|, C2=|Day-Year|, C3=|C1-C2|, C4=|Month-Year|."
    }


# ---------------------------------------------------------------------------
# 9. LO SHU GRID & PLANES OF EXPRESSION
# ---------------------------------------------------------------------------

def calculate_lo_shu_grid(year: int, month: int, day: int) -> Dict[str, Any]:
    """
    Calculate the traditional Chinese/Vedic Lo Shu Grid (3x3 magic square).
    Format:
    4 | 9 | 2
    3 | 5 | 7
    8 | 1 | 6
    """
    raw = f"{day:02d}{month:02d}{year:04d}"
    digits = [int(c) for c in raw if c != '0']
    counts = Counter(digits)

    layout = [
        [4, 9, 2],
        [3, 5, 7],
        [8, 1, 6]
    ]

    grid_matrix = [
        [{"number": n, "count": counts[n], "present": counts[n] > 0} for n in row]
        for row in layout
    ]

    missing = [n for n in range(1, 10) if counts[n] == 0]
    repeated = {str(n): counts[n] for n in range(1, 10) if counts[n] > 1}

    # Planes analysis
    planes = {
        "mental_plane": {"numbers": [4, 9, 2], "counts": [counts[4], counts[9], counts[2]], "complete": all(counts[n] > 0 for n in [4, 9, 2])},
        "emotional_plane": {"numbers": [3, 5, 7], "counts": [counts[3], counts[5], counts[7]], "complete": all(counts[n] > 0 for n in [3, 5, 7])},
        "practical_plane": {"numbers": [8, 1, 6], "counts": [counts[8], counts[1], counts[6]], "complete": all(counts[n] > 0 for n in [8, 1, 6])},
        "thought_plane": {"numbers": [4, 3, 8], "counts": [counts[4], counts[3], counts[8]], "complete": all(counts[n] > 0 for n in [4, 3, 8])},
        "will_plane": {"numbers": [9, 5, 1], "counts": [counts[9], counts[5], counts[1]], "complete": all(counts[n] > 0 for n in [9, 5, 1])},
        "action_plane": {"numbers": [2, 7, 6], "counts": [counts[2], counts[7], counts[6]], "complete": all(counts[n] > 0 for n in [2, 7, 6])},
        "golden_raj_yoga": {"numbers": [4, 5, 6], "counts": [counts[4], counts[5], counts[6]], "complete": all(counts[n] > 0 for n in [4, 5, 6])},
        "silver_property_line": {"numbers": [2, 5, 8], "counts": [counts[2], counts[5], counts[8]], "complete": all(counts[n] > 0 for n in [2, 5, 8])},
    }

    return {
        "source_digits": raw,
        "zeros_ignored": True,
        "layout": grid_matrix,
        "counts": {str(n): counts[n] for n in range(1, 10)},
        "missing": missing,
        "repeated": repeated,
        "planes": planes,
    }


# ---------------------------------------------------------------------------
# 10. REMEDY & PRACTICAL GUIDANCE SELECTION
# ---------------------------------------------------------------------------

def normalize_action(text: str) -> str:
    """Normalize text for deduplication."""
    return re.sub(r"[^a-z0-9]", "", text.lower())

def select_guidance(
    missing_numbers: List[int],
    repeated_numbers: Dict[str, int],
    include_traditional: bool = False
) -> List[Dict[str, Any]]:
    """
    Select source-traceable remedies from the knowledge base:
    - Practical guidance is prioritized first.
    - Traditional symbolic remedies are included only if requested.
    - Deduplicates remedies by action string.
    - Segregates astrology-only doshas.
    """
    kb = load_knowledge_base()
    all_remedies = kb.get("remedies", [])
    
    selected = []
    seen_actions = set()

    # 1. Missing numbers remedies
    for num in missing_numbers:
        matches = [
            r for r in all_remedies
            if r.get("category") == "missing_number" and r.get("number") == num
        ]
        for r in matches:
            if not include_traditional and r.get("kind") != "practical":
                continue
            norm = normalize_action(r.get("en", ""))
            if norm and norm not in seen_actions:
                seen_actions.add(norm)
                selected.append(r)

    # 2. Repeated numbers guidance
    for num_str, count in repeated_numbers.items():
        num = int(num_str)
        matches = [
            r for r in all_remedies
            if r.get("category") == "repeated_number" and r.get("number") == num
        ]
        for r in matches:
            if not include_traditional and r.get("kind") != "practical":
                continue
            norm = normalize_action(r.get("en", ""))
            if norm and norm not in seen_actions:
                seen_actions.add(norm)
                selected.append(r)

    return selected


# ---------------------------------------------------------------------------
# 11. COMPLETE COMPREHENSIVE PROFILE BUILDER
# ---------------------------------------------------------------------------

def build_complete_numerology_profile(
    name: str,
    dob_str: str,
    target_year: Optional[int] = None,
    system: str = "both",
    life_path_policy: str = "component_reduction",
    confirmed_latin_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build complete master numerology profile combining all systems and analytics.
    - System: 'pythagorean', 'chaldean', or 'both'.
    - dob_str: 'YYYY-MM-DD'
    """
    try:
        dt = datetime.strptime(dob_str, "%Y-%m-%d").date()
    except Exception:
        raise ValueError(f"Invalid birth date format '{dob_str}'. Expected YYYY-MM-DD")

    year, month, day = dt.year, dt.month, dt.day
    if target_year is None:
        target_year = datetime.now().year

    # Script and Transliteration Check
    raw_name = name.strip()
    script = detect_script(raw_name)
    
    effective_name = confirmed_latin_name or raw_name
    name_calc_status = "calculated_from_latin_input"
    translit_info = None

    if script != "Latin" and not confirmed_latin_name:
        translit_info = transliterate_indic_name(raw_name)
        effective_name = translit_info["proposed_latin"]
        name_calc_status = "transliteration_used_requires_confirmation"

    # Core Date Numbers
    birth_num = calculate_birth_number(day)
    life_path_comp = calculate_life_path(year, month, day, policy="component_reduction")
    life_path_all = calculate_life_path(year, month, day, policy="all_digits")
    primary_life_path = life_path_comp if life_path_policy == "component_reduction" else life_path_all

    # Cycles
    pers_year = calculate_personal_year(day, month, target_year)
    pers_months = [calculate_personal_month(pers_year["trace"]["result"], m) for m in range(1, 13)]
    life_cycles = calculate_life_cycles(month, day, year)
    pinnacles_challenges = calculate_pinnacles_and_challenges(day, month, year)

    # Lo Shu Grid
    lo_shu = calculate_lo_shu_grid(year, month, day)

    # Name Numerology Calculations
    pyth_profile = None
    chald_profile = None

    try:
        if system in ("pythagorean", "both"):
            pyth_total = calculate_name_total(effective_name, PYTHAGOREAN_TABLE)
            pyth_comp = calculate_name_components(effective_name, PYTHAGOREAN_TABLE)
            pyth_karmic = calculate_name_karmic_profile(effective_name, PYTHAGOREAN_TABLE)
            pyth_profile = {
                "name_total": pyth_total,
                "components": pyth_comp,
                "karmic_profile": pyth_karmic,
            }
    except Exception as e:
        pyth_profile = {"error": str(e)}

    try:
        if system in ("chaldean", "both"):
            chald_total = calculate_name_total(effective_name, CHALDEAN_TABLE)
            chald_comp = calculate_name_components(effective_name, CHALDEAN_TABLE)
            chald_karmic = calculate_name_karmic_profile(effective_name, CHALDEAN_TABLE)
            chald_profile = {
                "name_total": chald_total,
                "components": chald_comp,
                "karmic_profile": chald_karmic,
            }
    except Exception as e:
        chald_profile = {"error": str(e)}

    # Remedies
    guidance = select_guidance(lo_shu["missing"], lo_shu["repeated"], include_traditional=True)

    kb = load_knowledge_base()
    themes = kb.get("number_themes", {})

    return {
        "meta": {
            "name": raw_name,
            "effective_latin_name": effective_name,
            "script_detected": script,
            "name_calculation_status": name_calc_status,
            "transliteration_info": translit_info,
            "birth_date": dob_str,
            "year": year,
            "month": month,
            "day": day,
            "target_year": target_year,
            "system_requested": system,
            "life_path_policy": life_path_policy,
            "calculated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "core_numbers": {
            "birth_number": birth_num,
            "life_path": primary_life_path,
            "life_path_component_reduction": life_path_comp,
            "life_path_all_digits": life_path_all,
        },
        "pythagorean": pyth_profile,
        "chaldean": chald_profile,
        "temporal_cycles": {
            "personal_year": pers_year,
            "personal_months": pers_months,
            "life_cycles": life_cycles,
            "pinnacles_and_challenges": pinnacles_challenges,
        },
        "lo_shu_grid": lo_shu,
        "remedies_and_guidance": guidance,
        "number_themes": themes,
        "policy_notices": {
            "traditions_separated": True,
            "no_guarantees": "Numerology is a symbolic interpretive tradition, not a scientific diagnostic tool.",
            "practical_priority": "Practical disciplined habits take precedence over symbolic remedies."
        }
    }
