# -*- coding: utf-8 -*-
"""
Vedas Kundli - Dedicated Ashtakoota 36-Guna Calculation Engine
Classical References: Muhurta Chintamani, Brihat Parashara Hora Shastra, Jataka Parijata.

Implements 8 separate, mathematically verified Koota calculation functions.
Never uses predetermined scores or hardcoded results.
"""

from typing import Dict, Any, Tuple, Optional, Set

# ---------------------------------------------------------------------------
# 0. INPUT VALIDATION & NORMALIZATION POLICY
# ---------------------------------------------------------------------------
class AshtakootaInputError(ValueError):
    """Raised when Moon position inputs to Ashtakoota calculations are missing, invalid, or conflicting."""
    pass

RASHI_NAMES_EN = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]
RASHI_NAMES_HI = [
    "मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या",
    "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"
]

NAKSHATRA_NAMES_EN = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]
NAKSHATRA_NAMES_HI = [
    "अश्विनी", "भरणी", "कृत्तिका", "रोहिणी", "मृगशिरा", "आर्द्रा",
    "पुनर्वसु", "पुष्य", "अश्लेषा", "मघा", "पूर्वा फाल्गुनी", "उत्तरा फाल्गुनी",
    "हस्त", "चित्रा", "स्वाती", "विशाखा", "अनुराधा", "ज्येष्ठा",
    "मूल", "पूर्वाषाढ़ा", "उत्तराषाढ़ा", "श्रवण", "धनिष्ठा", "शतभिषा",
    "पूर्वा भाद्रपद", "उत्तरा भाद्रपद", "रेवती"
]


def get_valid_signs_for_nakshatra(nak_idx: int) -> Set[int]:
    """
    Returns the set of 0-based sign indices (0..11) that Nakshatra nak_idx (0..26) spans.
    Each Nakshatra spans 13°20' (40/3 degrees).
    """
    start_deg = nak_idx * (40.0 / 3.0)
    end_deg = (nak_idx + 1) * (40.0 / 3.0)
    start_sign = int(start_deg / 30.0) % 12
    end_sign = int((end_deg - 1e-7) / 30.0) % 12
    return {start_sign, end_sign} if start_sign != end_sign else {start_sign}


def normalize_moon_input(
    moon_data: Any,
    entity_name: str = "moon",
    require_sign: bool = True,
    require_nakshatra: bool = True
) -> Dict[str, Any]:
    """
    Explicit, uncompromising input normalization policy for Ashtakoota engine:
    1. Validates presence and types of input data.
    2. Resolves Moon Rashi from sign_idx (0-based: 0..11), sign_num (1-based: 1..12), or sid_lon (0..360°).
    3. Resolves Nakshatra from nakshatra_idx (0-based: 0..26), nakshatra_num (1-based: 1..27), or sid_lon.
    4. Detects internal conflicts (e.g. sign_idx != sign_num - 1, or sign_idx != int(sid_lon/30)).
    5. Detects astronomical conflicts (e.g. Ashwini in Virgo).
    6. Never silently defaults missing or invalid inputs to 0 (Aries).
    """
    if not isinstance(moon_data, dict):
        raise AshtakootaInputError(f"Invalid input type for {entity_name}: expected dict, got {type(moon_data).__name__}")

    # Short-circuit if already validated and normalized
    if moon_data.get("_ashtakoota_normalized") is True:
        if require_sign and "sign_idx" not in moon_data:
            raise AshtakootaInputError(f"Missing required Moon sign in {entity_name}")
        if require_nakshatra and "nakshatra_idx" not in moon_data:
            raise AshtakootaInputError(f"Missing required Nakshatra in {entity_name}")
        return moon_data

    # --- 1. Longitude Resolution & Range Validation ---
    lon = None
    for lon_key in ("sid_lon", "moon_lon", "lon"):
        if lon_key in moon_data and moon_data[lon_key] is not None:
            raw_lon = moon_data[lon_key]
            if not isinstance(raw_lon, (int, float)) or isinstance(raw_lon, bool):
                raise AshtakootaInputError(f"Invalid longitude type for {entity_name}.{lon_key}: expected float/int, got {type(raw_lon).__name__}")
            if raw_lon < 0.0 or raw_lon >= 360.0:
                raise AshtakootaInputError(f"Invalid longitude value for {entity_name}.{lon_key}: {raw_lon}° (must be between 0.0 and 359.9999°)")
            lon = float(raw_lon)
            break

    # --- 2. Moon Sign Resolution & Conflict Detection ---
    sign_from_idx = None
    if "sign_idx" in moon_data and moon_data["sign_idx"] is not None:
        raw_s_idx = moon_data["sign_idx"]
        if not isinstance(raw_s_idx, int) or isinstance(raw_s_idx, bool):
            raise AshtakootaInputError(f"Invalid sign_idx type in {entity_name}: expected int, got {type(raw_s_idx).__name__}")
        if raw_s_idx < 0 or raw_s_idx > 11:
            raise AshtakootaInputError(f"Invalid sign_idx {raw_s_idx} in {entity_name}; must be between 0 (Aries) and 11 (Pisces)")
        sign_from_idx = raw_s_idx

    sign_from_num = None
    if "sign_num" in moon_data and moon_data["sign_num"] is not None:
        raw_s_num = moon_data["sign_num"]
        if not isinstance(raw_s_num, int) or isinstance(raw_s_num, bool):
            raise AshtakootaInputError(f"Invalid sign_num type in {entity_name}: expected int, got {type(raw_s_num).__name__}")
        if raw_s_num < 1 or raw_s_num > 12:
            raise AshtakootaInputError(f"Invalid sign_num {raw_s_num} in {entity_name}; must be between 1 (Aries) and 12 (Pisces)")
        sign_from_num = raw_s_num - 1

    # Conflict check between sign_idx and sign_num
    if sign_from_idx is not None and sign_from_num is not None:
        if sign_from_idx != sign_from_num:
            raise AshtakootaInputError(
                f"Conflicting sign inputs in {entity_name}: sign_idx={sign_from_idx} ({RASHI_NAMES_EN[sign_from_idx]}) "
                f"conflicts with sign_num={moon_data['sign_num']} ({RASHI_NAMES_EN[sign_from_num]})"
            )

    resolved_sign_idx = sign_from_idx if sign_from_idx is not None else sign_from_num

    # Conflict check between sign and longitude
    if lon is not None:
        derived_sign = int(lon / 30.0) % 12
        if resolved_sign_idx is not None:
            deg_rem = lon % 30.0
            if resolved_sign_idx != derived_sign:
                # Boundary tolerance (e.g. 29.9999999 vs 30.0)
                if abs(deg_rem - 30.0) < 1e-6 and resolved_sign_idx == (derived_sign + 1) % 12:
                    resolved_sign_idx = derived_sign
                elif deg_rem < 1e-6 and resolved_sign_idx == (derived_sign - 1 + 12) % 12:
                    resolved_sign_idx = derived_sign
                else:
                    raise AshtakootaInputError(
                        f"Conflicting sign inputs in {entity_name}: provided sign ({RASHI_NAMES_EN[resolved_sign_idx]}) "
                        f"does not match longitude {lon:.4f}° ({RASHI_NAMES_EN[derived_sign]})"
                    )
        else:
            resolved_sign_idx = derived_sign

    # --- 3. Nakshatra Resolution & Conflict Detection ---
    nak_from_idx = None
    if "nakshatra_idx" in moon_data and moon_data["nakshatra_idx"] is not None:
        raw_n_idx = moon_data["nakshatra_idx"]
        if not isinstance(raw_n_idx, int) or isinstance(raw_n_idx, bool):
            raise AshtakootaInputError(f"Invalid nakshatra_idx type in {entity_name}: expected int, got {type(raw_n_idx).__name__}")
        if raw_n_idx < 0 or raw_n_idx > 26:
            raise AshtakootaInputError(f"Invalid nakshatra_idx {raw_n_idx} in {entity_name}; must be between 0 (Ashwini) and 26 (Revati)")
        nak_from_idx = raw_n_idx

    nak_from_num = None
    if "nakshatra_num" in moon_data and moon_data["nakshatra_num"] is not None:
        raw_n_num = moon_data["nakshatra_num"]
        if not isinstance(raw_n_num, int) or isinstance(raw_n_num, bool):
            raise AshtakootaInputError(f"Invalid nakshatra_num type in {entity_name}: expected int, got {type(raw_n_num).__name__}")
        if raw_n_num < 1 or raw_n_num > 27:
            raise AshtakootaInputError(f"Invalid nakshatra_num {raw_n_num} in {entity_name}; must be between 1 (Ashwini) and 27 (Revati)")
        nak_from_num = raw_n_num - 1

    # Conflict check between nakshatra_idx and nakshatra_num
    if nak_from_idx is not None and nak_from_num is not None:
        if nak_from_idx != nak_from_num:
            raise AshtakootaInputError(
                f"Conflicting nakshatra inputs in {entity_name}: nakshatra_idx={nak_from_idx} ({NAKSHATRA_NAMES_EN[nak_from_idx]}) "
                f"conflicts with nakshatra_num={moon_data['nakshatra_num']} ({NAKSHATRA_NAMES_EN[nak_from_num]})"
            )

    resolved_nak_idx = nak_from_idx if nak_from_idx is not None else nak_from_num

    # Conflict check between nakshatra and longitude
    if lon is not None:
        nak_span = 360.0 / 27.0
        derived_nak = int(lon / nak_span) % 27
        if resolved_nak_idx is not None:
            if resolved_nak_idx != derived_nak:
                deg_rem_nak = lon % nak_span
                if abs(deg_rem_nak - nak_span) < 1e-6 and resolved_nak_idx == (derived_nak + 1) % 27:
                    resolved_nak_idx = derived_nak
                elif deg_rem_nak < 1e-6 and resolved_nak_idx == (derived_nak - 1 + 27) % 27:
                    resolved_nak_idx = derived_nak
                else:
                    raise AshtakootaInputError(
                        f"Conflicting nakshatra inputs in {entity_name}: provided nakshatra ({NAKSHATRA_NAMES_EN[resolved_nak_idx]}) "
                        f"does not match longitude {lon:.4f}° ({NAKSHATRA_NAMES_EN[derived_nak]})"
                    )
        else:
            resolved_nak_idx = derived_nak

    # Check presence of required sign and nakshatra
    if require_sign and resolved_sign_idx is None:
        raise AshtakootaInputError(
            f"Missing required Moon sign in {entity_name}: must provide 'sign_idx' (0..11), 'sign_num' (1..12), or 'sid_lon' (0..360°)"
        )

    if require_nakshatra and resolved_nak_idx is None:
        raise AshtakootaInputError(
            f"Missing required Nakshatra in {entity_name}: must provide 'nakshatra_idx' (0..26), 'nakshatra_num' (1..27), or 'sid_lon' (0..360°)"
        )

    # --- 4. Rashi-Nakshatra Astronomical Feasibility Check ---
    if resolved_sign_idx is not None and resolved_nak_idx is not None:
        valid_signs = get_valid_signs_for_nakshatra(resolved_nak_idx)
        if resolved_sign_idx not in valid_signs:
            valid_names = [RASHI_NAMES_EN[s] for s in sorted(valid_signs)]
            raise AshtakootaInputError(
                f"Astronomically impossible input in {entity_name}: Nakshatra {resolved_nak_idx} ({NAKSHATRA_NAMES_EN[resolved_nak_idx]}) "
                f"only spans sign(s) {valid_names}, but sign {resolved_sign_idx} ({RASHI_NAMES_EN[resolved_sign_idx]}) was provided"
            )

    # --- 5. Degree in Sign & Pada ---
    deg_in_sign = 0.0
    if "deg_in_sign" in moon_data and moon_data["deg_in_sign"] is not None:
        raw_deg = float(moon_data["deg_in_sign"])
        if raw_deg < 0.0 or raw_deg > 30.0:
            raise AshtakootaInputError(f"Invalid deg_in_sign in {entity_name}: {raw_deg}° (must be between 0.0 and 30.0)")
        deg_in_sign = raw_deg
    elif lon is not None:
        deg_in_sign = lon % 30.0

    pada = 1
    if "pada" in moon_data and moon_data["pada"] is not None:
        raw_pada = int(moon_data["pada"])
        if raw_pada < 1 or raw_pada > 4:
            raise AshtakootaInputError(f"Invalid pada in {entity_name}: {raw_pada} (must be 1, 2, 3, or 4)")
        pada = raw_pada
    elif lon is not None:
        nak_span = 360.0 / 27.0
        deg_in_nak = lon % nak_span
        pada = int(deg_in_nak / (nak_span / 4.0)) + 1
        pada = min(4, max(1, pada))

    # Construct normalized payload
    normalized = dict(moon_data)
    normalized["_ashtakoota_normalized"] = True
    if resolved_sign_idx is not None:
        normalized["sign_idx"] = resolved_sign_idx
        normalized["sign_num"] = resolved_sign_idx + 1
        normalized["sign_en"] = RASHI_NAMES_EN[resolved_sign_idx]
        normalized["sign_hi"] = RASHI_NAMES_HI[resolved_sign_idx]
    if resolved_nak_idx is not None:
        normalized["nakshatra_idx"] = resolved_nak_idx
        normalized["nakshatra_num"] = resolved_nak_idx + 1
        normalized["nakshatra_en"] = NAKSHATRA_NAMES_EN[resolved_nak_idx]
        normalized["nakshatra_hi"] = NAKSHATRA_NAMES_HI[resolved_nak_idx]
    normalized["deg_in_sign"] = deg_in_sign
    normalized["pada"] = pada
    if lon is not None:
        normalized["sid_lon"] = lon

    return normalized

# ---------------------------------------------------------------------------
# 1. VARNA DEFINITIONS & CONSTANTS
# ---------------------------------------------------------------------------
# Ranks: Brahmin = 4, Kshatriya = 3, Vaishya = 2, Shudra = 1
VARNA_RANKS = {
    "Brahmin": 4,
    "Kshatriya": 3,
    "Vaishya": 2,
    "Shudra": 1
}

VARNA_NAMES_HI = {
    "Brahmin": "ब्राह्मण",
    "Kshatriya": "क्षत्रिय",
    "Vaishya": "वैश्य",
    "Shudra": "शूद्र"
}

# 12 Rashis (0=Aries .. 11=Pisces)
# Brahmin: Cancer(3), Scorpio(7), Pisces(11)
# Kshatriya: Aries(0), Leo(4), Sagittarius(8)
# Vaishya: Taurus(1), Virgo(5), Capricorn(9)
# Shudra: Gemini(2), Libra(6), Aquarius(10)
RASHI_TO_VARNA = {
    0: "Kshatriya",  # Aries
    1: "Vaishya",    # Taurus
    2: "Shudra",     # Gemini
    3: "Brahmin",    # Cancer
    4: "Kshatriya",  # Leo
    5: "Vaishya",    # Virgo
    6: "Shudra",     # Libra
    7: "Brahmin",    # Scorpio
    8: "Kshatriya",  # Sagittarius
    9: "Vaishya",    # Capricorn
    10: "Shudra",    # Aquarius
    11: "Brahmin"    # Pisces
}


def calculate_varna_koota(groom_moon: Dict[str, Any], bride_moon: Dict[str, Any]) -> Dict[str, Any]:
    """
    Varna Koota (Max 1 point).
    Brahmin = 4, Kshatriya = 3, Vaishya = 2, Shudra = 1.
    Rule: Score = 1 if GroomRank >= BrideRank else 0.
    """
    b_norm = normalize_moon_input(groom_moon, "groom_moon", require_sign=True, require_nakshatra=False)
    g_norm = normalize_moon_input(bride_moon, "bride_moon", require_sign=True, require_nakshatra=False)
    b_rasi = b_norm["sign_idx"]
    g_rasi = g_norm["sign_idx"]

    b_varna = RASHI_TO_VARNA[b_rasi]
    g_varna = RASHI_TO_VARNA[g_rasi]

    b_rank = VARNA_RANKS[b_varna]
    g_rank = VARNA_RANKS[g_varna]

    score = 1.0 if b_rank >= g_rank else 0.0

    return {
        "koot_code": "VARNA",
        "koot_en": "Varna",
        "koot_hi": "वर्ण",
        "max": 1.0,
        "obtained": score,
        "groom_val": f"{b_varna} ({VARNA_NAMES_HI[b_varna]})",
        "bride_val": f"{g_varna} ({VARNA_NAMES_HI[g_varna]})",
        "groom_varna": b_varna,
        "bride_varna": g_varna,
        "groom_rank": b_rank,
        "bride_rank": g_rank,
        "favorable": (score == 1.0),
        "rule_id": "VARNA_CLASSICAL_01",
        "citation": "Muhurta Chintamani vivaha prakarana v. 32 / BPHS Ch. 81",
        "desc_en": "Spiritual ego, work orientation and psychological hierarchy.",
        "desc_hi": "कार्य प्रवृत्ति, आध्यात्मिक अभिरुचि व अहंकार सामंजस्य।"
    }


# ---------------------------------------------------------------------------
# 2. VASHYA DEFINITIONS & 5x5 MATRIX WITH DEGREE SUBDIVISIONS
# ---------------------------------------------------------------------------
# Five traditional Vashya groups:
# 1. Chatushpada (Quadrupeds)
# 2. Manava (Dvipada / Humans)
# 3. Jalachara (Water dwellers)
# 4. Vanachara (Wild beasts / Lion)
# 5. Keeta (Insects / Scorpio)
VASHYA_GROUPS = ["Chatushpada", "Manava", "Jalachara", "Vanachara", "Keeta"]
VASHYA_GROUPS_HI = {
    "Chatushpada": "चतुष्पाद",
    "Manava": "मानव (द्विपद)",
    "Jalachara": "जलचर",
    "Vanachara": "वनचर (सिंह)",
    "Keeta": "कीट"
}

# 5x5 Compatibility Matrix (Row = Bride, Column = Groom)
# Classes: 0: Chatushpada, 1: Manava, 2: Jalachara, 3: Vanachara, 4: Keeta
VASHYA_5X5_MATRIX = [
    # Bride: Chatushpada (0)
    [2.0, 0.5, 2.0, 0.0, 2.0],
    # Bride: Manava (1)
    [0.5, 2.0, 0.5, 0.0, 1.0],
    # Bride: Jalachara (2)
    [2.0, 0.5, 2.0, 0.0, 2.0],
    # Bride: Vanachara (3)
    [0.0, 0.0, 0.0, 2.0, 0.0],
    # Bride: Keeta (4)
    [2.0, 1.0, 2.0, 0.0, 2.0],
]


def classify_vashya_group(rashi_idx: int, deg_in_sign: float) -> str:
    """
    Classify Moon into one of 5 traditional Vashya groups:
    - Aries (0): Chatushpada
    - Taurus (1): Chatushpada
    - Gemini (2): Manava
    - Cancer (3): Jalachara
    - Leo (4): Vanachara
    - Virgo (5): Manava
    - Libra (6): Manava
    - Scorpio (7): Keeta
    - Sagittarius (8):
        0° to 15°: Manava
        15° to 30°: Chatushpada
    - Capricorn (9):
        0° to 15°: Chatushpada
        15° to 30°: Jalachara
    - Aquarius (10): Manava (or Jalachara in some, classical standard is Manava / Jalachara Kumbha)
    - Pisces (11): Jalachara
    """
    if rashi_idx in (0, 1):
        return "Chatushpada"
    elif rashi_idx == 2:
        return "Manava"
    elif rashi_idx == 3:
        return "Jalachara"
    elif rashi_idx == 4:
        return "Vanachara"
    elif rashi_idx in (5, 6):
        return "Manava"
    elif rashi_idx == 7:
        return "Keeta"
    elif rashi_idx == 8:
        return "Manava" if deg_in_sign < 15.0 else "Chatushpada"
    elif rashi_idx == 9:
        return "Chatushpada" if deg_in_sign < 15.0 else "Jalachara"
    elif rashi_idx == 10:
        return "Manava"
    elif rashi_idx == 11:
        return "Jalachara"
    return "Manava"


def calculate_vashya_koota(groom_moon: Dict[str, Any], bride_moon: Dict[str, Any]) -> Dict[str, Any]:
    """
    Vashya Koota (Max 2 points).
    Evaluates mutual attraction, magnetic power and control using the 5-class system
    with exact degree subdivisions in Sagittarius and Capricorn.
    """
    b_norm = normalize_moon_input(groom_moon, "groom_moon", require_sign=True, require_nakshatra=False)
    g_norm = normalize_moon_input(bride_moon, "bride_moon", require_sign=True, require_nakshatra=False)
    b_rasi = b_norm["sign_idx"]
    g_rasi = g_norm["sign_idx"]

    b_deg = float(b_norm["deg_in_sign"])
    g_deg = float(g_norm["deg_in_sign"])

    b_group = classify_vashya_group(b_rasi, b_deg)
    g_group = classify_vashya_group(g_rasi, g_deg)

    b_idx = VASHYA_GROUPS.index(b_group)
    g_idx = VASHYA_GROUPS.index(g_group)

    # Matrix: Row = Bride, Column = Groom
    score = float(VASHYA_5X5_MATRIX[g_idx][b_idx])

    return {
        "koot_code": "VASHYA",
        "koot_en": "Vashya",
        "koot_hi": "वश्य",
        "max": 2.0,
        "obtained": score,
        "groom_val": f"{b_group} ({VASHYA_GROUPS_HI[b_group]})",
        "bride_val": f"{g_group} ({VASHYA_GROUPS_HI[g_group]})",
        "groom_group": b_group,
        "bride_group": g_group,
        "groom_deg_in_sign": b_deg,
        "bride_deg_in_sign": g_deg,
        "favorable": (score >= 1.0),
        "rule_id": "VASHYA_5X5_SUBDIVIDED",
        "citation": "Brihat Parashara Hora Shastra Ch. 81 / Muhurta Chintamani / Nemichandra Shastri",
        "desc_en": "Mutual attraction, influence, fidelity and power of natural attachment.",
        "desc_hi": "परस्पर आकर्षण, निष्ठा, समर्पण व प्रभाव सामंजस्य।"
    }


# ---------------------------------------------------------------------------
# 3. TARA / DINA KOOTA
# ---------------------------------------------------------------------------
TARA_NAMES_EN = {
    1: "Janma (Birth)",
    2: "Sampat (Wealth/Prosperity)",
    3: "Vipat (Danger/Misfortune)",
    4: "Kshema (Well-being/Security)",
    5: "Pratyak (Obstacles/Enmity)",
    6: "Sadhana (Accomplishment/Success)",
    7: "Naidhana (Peril/Destruction)",
    8: "Mitra (Friend)",
    9: "Parama Mitra (Supreme Friend)"
}

TARA_NAMES_HI = {
    1: "जन्म", 2: "सम्पत", 3: "विपत्", 4: "क्षेम", 5: "प्रत्यरि",
    6: "साधक", 7: "वध / नैधन", 8: "मित्र", 9: "परम मित्र"
}

# Unfavourable taras: 3, 5, 7 receive 0 points; others receive 1.5 points per direction
UNFAVOURABLE_TARAS = {3, 5, 7}


def calculate_tara_koota(groom_moon: Dict[str, Any], bride_moon: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tara / Dina Koota (Max 3 points).
    Calculates star distance in both directions:
      - Groom to Bride: Start = Groom Nakshatra, Target = Bride Nakshatra.
      - Bride to Groom: Start = Bride Nakshatra, Target = Groom Nakshatra.
    Formula:
      Count = ((Target - Start + 27) % 27) + 1
      Tara = ((Count - 1) % 9) + 1
    Points: 1.5 per direction if favorable (1,2,4,6,8,9), 0.0 if unfavorable (3,5,7).
    Total = GroomToBrideScore + BrideToGroomScore.

    Example:
      Groom: Punarvasu (7), Bride: Mrigashira (5)
      - Groom to Bride: ((5 - 7 + 27) % 27) + 1 = 26th Tara = Mitra (1.5 pts)
      - Bride to Groom: ((7 - 5 + 27) % 27) + 1 = 3rd Tara = Vipat (0.0 pts)
      Total = 1.5 / 3.0 points.
    """
    b_norm = normalize_moon_input(groom_moon, "groom_moon", require_sign=False, require_nakshatra=True)
    g_norm = normalize_moon_input(bride_moon, "bride_moon", require_sign=False, require_nakshatra=True)
    b_nak = b_norm["nakshatra_idx"]
    g_nak = g_norm["nakshatra_idx"]

    # 1. Groom to Bride (Start = Groom, Target = Bride)
    count_groom_to_bride = ((g_nak - b_nak + 27) % 27) + 1
    tara_groom_to_bride = ((count_groom_to_bride - 1) % 9) + 1
    score_g_to_b = 0.0 if tara_groom_to_bride in UNFAVOURABLE_TARAS else 1.5

    # 2. Bride to Groom (Start = Bride, Target = Groom)
    count_bride_to_groom = ((b_nak - g_nak + 27) % 27) + 1
    tara_bride_to_groom = ((count_bride_to_groom - 1) % 9) + 1
    score_b_to_g = 0.0 if tara_bride_to_groom in UNFAVOURABLE_TARAS else 1.5

    total_tara = score_g_to_b + score_b_to_g

    explanation = (
        f"Groom to Bride: {count_groom_to_bride}th Tara = {TARA_NAMES_EN[tara_groom_to_bride]} ({score_g_to_b} pts); "
        f"Bride to Groom: {count_bride_to_groom}th Tara = {TARA_NAMES_EN[tara_bride_to_groom]} ({score_b_to_g} pts). "
        f"Combined Tara score: {total_tara:.1f} / 3.0 points."
    )

    return {
        "koot_code": "TARA",
        "koot_en": "Tara",
        "koot_hi": "तारा (दीना)",
        "max": 3.0,
        "obtained": total_tara,
        "groom_val": f"{TARA_NAMES_EN[tara_groom_to_bride]} ({count_groom_to_bride}th)",
        "bride_val": f"{TARA_NAMES_EN[tara_bride_to_groom]} ({count_bride_to_groom}th)",
        "groom_classification": f"Groom to Bride: {count_groom_to_bride}th Tara = {TARA_NAMES_EN[tara_groom_to_bride]}",
        "bride_classification": f"Bride to Groom: {count_bride_to_groom}th Tara = {TARA_NAMES_EN[tara_bride_to_groom]}",
        "groom_to_bride_count": count_groom_to_bride,
        "groom_to_bride_tara": tara_groom_to_bride,
        "groom_to_bride_score": score_g_to_b,
        "bride_to_groom_count": count_bride_to_groom,
        "bride_to_groom_tara": tara_bride_to_groom,
        "bride_to_groom_score": score_b_to_g,
        "forward_count": count_bride_to_groom,
        "forward_tara": tara_bride_to_groom,
        "forward_score": score_b_to_g,
        "reverse_count": count_groom_to_bride,
        "reverse_tara": tara_groom_to_bride,
        "reverse_score": score_g_to_b,
        "favorable": (total_tara >= 1.5),
        "rule_id": "TARA_CONVENTIONAL_BIDIRECTIONAL",
        "citation": "Muhurta Chintamani vivaha prakarana v. 34 / B.V. Raman Muhurtha",
        "desc_en": "Birth star destiny, longevity, health harmony and misfortune shielding.",
        "desc_hi": "भाग्य, स्वास्थ्य, दीर्घायु व नक्षत्र सुरक्षा सामंजस्य।",
        "explanation": explanation
    }


# ---------------------------------------------------------------------------
# 4. YONI KOOTA
# ---------------------------------------------------------------------------
YONI_ANIMALS = [
    "Horse", "Elephant", "Sheep", "Serpent", "Dog", "Cat", "Rat",
    "Cow", "Buffalo", "Tiger", "Deer", "Monkey", "Mongoose", "Lion"
]

YONI_ANIMALS_HI = {
    "Horse": "अश्व", "Elephant": "गज", "Sheep": "मेष", "Serpent": "सर्प",
    "Dog": "श्वान", "Cat": "मार्जारी", "Rat": "मूषक", "Cow": "गौ",
    "Buffalo": "महिष", "Tiger": "व्याघ्र", "Deer": "मृग", "Monkey": "वानर",
    "Mongoose": "नकुल", "Lion": "सिंह"
}

# 27 Nakshatras Yoni (0-indexed: Ashwini to Revati)
NAKSHATRA_TO_YONI = [
    "Horse",      # 0 Ashwini
    "Elephant",   # 1 Bharani
    "Sheep",      # 2 Krittika
    "Serpent",    # 3 Rohini
    "Serpent",    # 4 Mrigashira
    "Dog",        # 5 Ardra
    "Cat",        # 6 Punarvasu
    "Sheep",      # 7 Pushya
    "Cat",        # 8 Ashlesha
    "Rat",        # 9 Magha
    "Rat",        # 10 Purva Phalguni
    "Cow",        # 11 Uttara Phalguni
    "Buffalo",    # 12 Hasta
    "Tiger",      # 13 Chitra
    "Buffalo",    # 14 Swati
    "Tiger",      # 15 Vishakha
    "Deer",       # 16 Anuradha
    "Deer",       # 17 Jyeshtha
    "Dog",        # 18 Mula
    "Monkey",     # 19 Purva Ashadha
    "Mongoose",   # 20 Uttara Ashadha
    "Monkey",     # 21 Shravana
    "Lion",       # 22 Dhanishta
    "Horse",      # 23 Shatabhisha
    "Lion",       # 24 Purva Bhadrapada
    "Cow",        # 25 Uttara Bhadrapada
    "Elephant"    # 26 Revati
]

# 14x14 Matrix (Row = Bride, Column = Groom)
# Scores range 0 to 4
YONI_14X14_MATRIX = [
    # Horse(0), Elephant(1), Sheep(2), Serpent(3), Dog(4), Cat(5), Rat(6), Cow(7), Buffalo(8), Tiger(9), Deer(10), Monkey(11), Mongoose(12), Lion(13)
    [4, 2, 3, 2, 2, 3, 3, 3, 0, 1, 3, 2, 2, 1],  # 0 Horse
    [2, 4, 3, 2, 2, 3, 3, 3, 3, 2, 2, 2, 2, 0],  # 1 Elephant
    [3, 3, 4, 3, 2, 3, 1, 3, 3, 1, 3, 0, 3, 1],  # 2 Sheep
    [2, 2, 3, 4, 2, 2, 1, 1, 2, 2, 2, 2, 0, 2],  # 3 Serpent
    [2, 2, 2, 2, 4, 1, 1, 2, 2, 1, 0, 2, 2, 1],  # 4 Dog
    [2, 2, 3, 2, 1, 4, 0, 2, 2, 1, 2, 2, 2, 2],  # 5 Cat
    [2, 2, 2, 1, 1, 0, 4, 2, 2, 2, 2, 2, 2, 1],  # 6 Rat
    [3, 2, 3, 1, 2, 2, 2, 4, 3, 0, 3, 2, 3, 1],  # 7 Cow
    [0, 3, 3, 2, 2, 2, 2, 3, 4, 1, 2, 2, 2, 3],  # 8 Buffalo
    [1, 2, 1, 2, 1, 1, 2, 0, 1, 4, 2, 1, 2, 2],  # 9 Tiger
    [3, 2, 3, 2, 0, 2, 2, 3, 2, 1, 4, 2, 2, 2],  # 10 Deer
    [2, 3, 0, 2, 2, 2, 2, 2, 2, 1, 2, 4, 2, 3],  # 11 Monkey
    [2, 2, 3, 0, 2, 2, 2, 3, 2, 2, 2, 2, 4, 2],  # 12 Mongoose
    [1, 0, 1, 2, 1, 2, 1, 1, 3, 2, 2, 2, 2, 4]   # 13 Lion
]


def calculate_yoni_koota(groom_moon: Dict[str, Any], bride_moon: Dict[str, Any]) -> Dict[str, Any]:
    """
    Yoni Koota (Max 4 points).
    Compares biological, instinctual and physical intimacy compatibility
    via the 14 animal archetypes and full 14x14 classical table.
    """
    b_norm = normalize_moon_input(groom_moon, "groom_moon", require_sign=False, require_nakshatra=True)
    g_norm = normalize_moon_input(bride_moon, "bride_moon", require_sign=False, require_nakshatra=True)
    b_nak = b_norm["nakshatra_idx"]
    g_nak = g_norm["nakshatra_idx"]

    b_yoni = NAKSHATRA_TO_YONI[b_nak]
    g_yoni = NAKSHATRA_TO_YONI[g_nak]

    b_idx = YONI_ANIMALS.index(b_yoni)
    g_idx = YONI_ANIMALS.index(g_yoni)

    # Matrix: Row = Bride, Column = Groom
    score = float(YONI_14X14_MATRIX[g_idx][b_idx])

    return {
        "koot_code": "YONI",
        "koot_en": "Yoni",
        "koot_hi": "योनि",
        "max": 4.0,
        "obtained": score,
        "groom_val": f"{b_yoni} ({YONI_ANIMALS_HI[b_yoni]})",
        "bride_val": f"{g_yoni} ({YONI_ANIMALS_HI[g_yoni]})",
        "groom_yoni": b_yoni,
        "bride_yoni": g_yoni,
        "favorable": (score >= 2.0),
        "rule_id": "YONI_14X14_CLASSICAL",
        "citation": "Brihat Parashara Hora Shastra Ch. 81 v. 8 / Muhurta Chintamani",
        "desc_en": "Biological compatibility, sexual harmony and physical affection.",
        "desc_hi": "शारीरिक, जैविक व दांपत्य सुख आकर्षण सामंजस्य।"
    }


# ---------------------------------------------------------------------------
# 5. GRAHA MAITRI KOOTA
# ---------------------------------------------------------------------------
GRAHA_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

GRAHA_NAMES_HI = {
    "Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध",
    "Jupiter": "गुरु", "Venus": "शुक्र", "Saturn": "शनि"
}

RASHI_LORDS = [
    "Mars",     # 0 Aries
    "Venus",    # 1 Taurus
    "Mercury",  # 2 Gemini
    "Moon",     # 3 Cancer
    "Sun",      # 4 Leo
    "Mercury",  # 5 Virgo
    "Venus",    # 6 Libra
    "Mars",     # 7 Scorpio
    "Jupiter",  # 8 Sagittarius
    "Saturn",   # 9 Capricorn
    "Saturn",   # 10 Aquarius
    "Jupiter"   # 11 Pisces
]

# Natural Friendships Dictionary (Naisargika Sambandha)
NATURAL_RELATIONSHIPS = {
    "Sun": {
        "friends": {"Moon", "Mars", "Jupiter"},
        "neutrals": {"Mercury"},
        "enemies": {"Venus", "Saturn"}
    },
    "Moon": {
        "friends": {"Sun", "Mercury"},
        "neutrals": {"Mars", "Jupiter", "Venus", "Saturn"},
        "enemies": set()
    },
    "Mars": {
        "friends": {"Sun", "Moon", "Jupiter"},
        "neutrals": {"Venus", "Saturn"},
        "enemies": {"Mercury"}
    },
    "Mercury": {
        "friends": {"Sun", "Venus"},
        "neutrals": {"Mars", "Jupiter", "Saturn"},
        "enemies": {"Moon"}
    },
    "Jupiter": {
        "friends": {"Sun", "Moon", "Mars"},
        "neutrals": {"Saturn"},
        "enemies": {"Mercury", "Venus"}
    },
    "Venus": {
        "friends": {"Mercury", "Saturn"},
        "neutrals": {"Mars", "Jupiter"},
        "enemies": {"Sun", "Moon"}
    },
    "Saturn": {
        "friends": {"Mercury", "Venus"},
        "neutrals": {"Jupiter"},
        "enemies": {"Sun", "Moon", "Mars"}
    }
}


def are_planets_mutual_friends_or_same(p1: str, p2: str) -> bool:
    """Check if two planets are identical or mutually friendly."""
    if p1 == p2:
        return True
    p1_friends = NATURAL_RELATIONSHIPS.get(p1, {}).get("friends", set())
    p2_friends = NATURAL_RELATIONSHIPS.get(p2, {}).get("friends", set())
    return (p2 in p1_friends) and (p1 in p2_friends)

# Verified 7x7 Matrix (Row = Bride Lord, Column = Groom Lord)
# Order: Sun(0), Moon(1), Mars(2), Mercury(3), Jupiter(4), Venus(5), Saturn(6)
GRAHA_MAITRI_7X7_MATRIX = [
    [5.0, 5.0, 5.0, 4.0, 5.0, 0.0, 0.0],  # Sun
    [5.0, 5.0, 4.0, 1.0, 4.0, 0.5, 0.5],  # Moon
    [5.0, 4.0, 5.0, 0.5, 5.0, 3.0, 0.5],  # Mars
    [4.0, 1.0, 0.5, 5.0, 0.5, 5.0, 4.0],  # Mercury
    [5.0, 4.0, 5.0, 0.5, 5.0, 0.5, 3.0],  # Jupiter
    [0.0, 0.5, 3.0, 5.0, 0.5, 5.0, 5.0],  # Venus
    [0.0, 0.5, 0.5, 4.0, 3.0, 5.0, 5.0]   # Saturn
]


def calculate_graha_maitri_koota(groom_moon: Dict[str, Any], bride_moon: Dict[str, Any]) -> Dict[str, Any]:
    """
    Graha Maitri Koota (Max 5 points).
    Evaluates Moon sign lords and tests natural planetary relationships.
    Standard scoring table:
      - Same lord / mutual friendship: 5.0
      - Friend and neutral: 4.0
      - Both neutral: 3.0
      - Friend and enemy: 1.0
      - Neutral and enemy: 0.5
      - Both enemies: 0.0
    """
    b_norm = normalize_moon_input(groom_moon, "groom_moon", require_sign=True, require_nakshatra=False)
    g_norm = normalize_moon_input(bride_moon, "bride_moon", require_sign=True, require_nakshatra=False)
    b_rasi = b_norm["sign_idx"]
    g_rasi = g_norm["sign_idx"]

    b_lord = RASHI_LORDS[b_rasi]
    g_lord = RASHI_LORDS[g_rasi]

    b_idx = GRAHA_ORDER.index(b_lord)
    g_idx = GRAHA_ORDER.index(g_lord)

    # Matrix lookup (Row = Bride, Col = Groom)
    score = float(GRAHA_MAITRI_7X7_MATRIX[g_idx][b_idx])

    return {
        "koot_code": "GRAHA_MAITRI",
        "koot_en": "Graha Maitri",
        "koot_hi": "ग्रहमैत्री",
        "max": 5.0,
        "obtained": score,
        "groom_val": f"{b_lord} ({GRAHA_NAMES_HI[b_lord]})",
        "bride_val": f"{g_lord} ({GRAHA_NAMES_HI[g_lord]})",
        "groom_lord": b_lord,
        "bride_lord": g_lord,
        "favorable": (score >= 3.0),
        "rule_id": "GRAHA_MAITRI_6TIER",
        "citation": "Brihat Parashara Hora Shastra Ch. 81 / Muhurta Chintamani",
        "desc_en": "Mental harmony, intellectual compatibility and outlook alignment.",
        "desc_hi": "मानसिक सामंजस्य, वैचारिक तालमेल व जीवन दृष्टिकोण अनुकूलता।"
    }


# ---------------------------------------------------------------------------
# 6. GANA KOOTA
# ---------------------------------------------------------------------------
GANA_CLASSES = ["Deva", "Manushya", "Rakshasa"]
GANA_NAMES_HI = {"Deva": "देव", "Manushya": "मनुष्य", "Rakshasa": "राक्षस"}

# 27 Nakshatras Gana
NAKSHATRA_TO_GANA = [
    "Deva",      # 0 Ashwini
    "Manushya",  # 1 Bharani
    "Rakshasa",  # 2 Krittika
    "Manushya",  # 3 Rohini
    "Deva",      # 4 Mrigashira
    "Manushya",  # 5 Ardra
    "Deva",      # 6 Punarvasu
    "Deva",      # 7 Pushya
    "Rakshasa",  # 8 Ashlesha
    "Rakshasa",  # 9 Magha
    "Manushya",  # 10 Purva Phalguni
    "Manushya",  # 11 Uttara Phalguni
    "Deva",      # 12 Hasta
    "Rakshasa",  # 13 Chitra
    "Deva",      # 14 Swati
    "Rakshasa",  # 15 Vishakha
    "Deva",      # 16 Anuradha
    "Rakshasa",  # 17 Jyeshtha
    "Rakshasa",  # 18 Mula
    "Manushya",  # 19 Purva Ashadha
    "Manushya",  # 20 Uttara Ashadha
    "Deva",      # 21 Shravana
    "Rakshasa",  # 22 Dhanishta
    "Rakshasa",  # 23 Shatabhisha
    "Manushya",  # 24 Purva Bhadrapada
    "Manushya",  # 25 Uttara Bhadrapada
    "Deva"       # 26 Revati
]

# Row = Bride, Column = Groom
# Order: Deva(0), Manushya(1), Rakshasa(2)
GANA_3X3_MATRIX = [
    [6.0, 5.0, 1.0],  # Bride: Deva
    [6.0, 6.0, 0.0],  # Bride: Manushya
    [0.0, 0.0, 6.0]   # Bride: Rakshasa
]


def calculate_gana_koota(groom_moon: Dict[str, Any], bride_moon: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gana Koota (Max 6 points).
    Evaluates temperament, temperament clashes, and behavioral compatibility.
    Deva, Manushya, Rakshasa directional matrix.
    """
    b_norm = normalize_moon_input(groom_moon, "groom_moon", require_sign=False, require_nakshatra=True)
    g_norm = normalize_moon_input(bride_moon, "bride_moon", require_sign=False, require_nakshatra=True)
    b_nak = b_norm["nakshatra_idx"]
    g_nak = g_norm["nakshatra_idx"]

    b_gana = NAKSHATRA_TO_GANA[b_nak]
    g_gana = NAKSHATRA_TO_GANA[g_nak]

    b_idx = GANA_CLASSES.index(b_gana)
    g_idx = GANA_CLASSES.index(g_gana)

    score = float(GANA_3X3_MATRIX[g_idx][b_idx])

    return {
        "koot_code": "GANA",
        "koot_en": "Gana",
        "koot_hi": "गण",
        "max": 6.0,
        "obtained": score,
        "groom_val": f"{b_gana} ({GANA_NAMES_HI[b_gana]})",
        "bride_val": f"{g_gana} ({GANA_NAMES_HI[g_gana]})",
        "groom_gana": b_gana,
        "bride_gana": g_gana,
        "favorable": (score >= 5.0),
        "rule_id": "GANA_DIRECTIONAL_3X3",
        "citation": "Brihat Parashara Hora Shastra Ch. 81 v. 14 / Muhurta Chintamani",
        "desc_en": "Behavioral temperament, domestic harmony and compatibility in daily lifestyle.",
        "desc_hi": "स्वभाव, आचरण, सहिष्णुता व पारिवारिक सामंजस्य।"
    }


# ---------------------------------------------------------------------------
# 7. BHAKOOT KOOTA
# ---------------------------------------------------------------------------
# Inauspicious Bhakoot distances (1-indexed circular distance):
# 2/12 (Dwirdwadasha), 5/9 (Navam-Pancham), 6/8 (Shadashtaka)
ZERO_BHAKOOT_PAIRS = {(2, 12), (12, 2), (5, 9), (9, 5), (6, 8), (8, 6)}


def calculate_bhakoot_koota(groom_moon: Dict[str, Any], bride_moon: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bhakoot Koota (Max 7 points).
    Calculates circular distance between the two Moon signs in both directions.
    Conventional favourable: 1/1, 3/11, 4/10, 7/7 -> 7 points.
    Dosha relationships: 2/12, 5/9, 6/8 -> 0 points.
    """
    b_norm = normalize_moon_input(groom_moon, "groom_moon", require_sign=True, require_nakshatra=False)
    g_norm = normalize_moon_input(bride_moon, "bride_moon", require_sign=True, require_nakshatra=False)
    b_rasi = b_norm["sign_idx"]
    g_rasi = g_norm["sign_idx"]

    dist_groom_to_bride = ((g_rasi - b_rasi + 12) % 12) + 1
    dist_bride_to_groom = ((b_rasi - g_rasi + 12) % 12) + 1

    bhakoot_pair = (dist_groom_to_bride, dist_bride_to_groom)
    has_dosha = bhakoot_pair in ZERO_BHAKOOT_PAIRS

    score = 0.0 if has_dosha else 7.0
    pair_label = f"{dist_groom_to_bride}/{dist_bride_to_groom}"

    return {
        "koot_code": "BHAKOOT",
        "koot_en": "Bhakoot",
        "koot_hi": "भकूट",
        "max": 7.0,
        "obtained": score,
        "groom_val": f"{dist_groom_to_bride}th ({groom_moon.get('sign_en', '')})",
        "bride_val": f"{dist_bride_to_groom}th ({bride_moon.get('sign_en', '')})",
        "dist_groom_to_bride": dist_groom_to_bride,
        "dist_bride_to_groom": dist_bride_to_groom,
        "pair_label": pair_label,
        "has_dosha": has_dosha,
        "favorable": (score == 7.0),
        "rule_id": "BHAKOOT_CIRCULAR_12",
        "citation": "Muhurta Chintamani vivaha prakarana v. 32",
        "desc_en": "Family prosperity, emotional stability, health and lineage growth.",
        "desc_hi": "पारिवारिक समृद्धि, वंश वृद्धि, स्वास्थ्य व भावनात्मक संबंध।"
    }


# ---------------------------------------------------------------------------
# 8. NADI KOOTA
# ---------------------------------------------------------------------------
NADI_CLASSES = ["Adi", "Madhya", "Antya"]
NADI_NAMES_HI = {"Adi": "आदि", "Madhya": "मध्य", "Antya": "अंत्य"}

# 27 Nakshatras Nadi
NAKSHATRA_TO_NADI = [
    "Adi",     # 0 Ashwini
    "Madhya",  # 1 Bharani
    "Antya",   # 2 Krittika
    "Antya",   # 3 Rohini
    "Madhya",  # 4 Mrigashira
    "Adi",     # 5 Ardra
    "Adi",     # 6 Punarvasu
    "Madhya",  # 7 Pushya
    "Antya",   # 8 Ashlesha
    "Antya",   # 9 Magha
    "Madhya",  # 10 Purva Phalguni
    "Adi",     # 11 Uttara Phalguni
    "Adi",     # 12 Hasta
    "Madhya",  # 13 Chitra
    "Antya",   # 14 Swati
    "Antya",   # 15 Vishakha
    "Madhya",  # 16 Anuradha
    "Adi",     # 17 Jyeshtha
    "Adi",     # 18 Mula
    "Madhya",  # 19 Purva Ashadha
    "Antya",   # 20 Uttara Ashadha
    "Antya",   # 21 Shravana
    "Madhya",  # 22 Dhanishta
    "Adi",     # 23 Shatabhisha
    "Adi",     # 24 Purva Bhadrapada
    "Madhya",  # 25 Uttara Bhadrapada
    "Antya"    # 26 Revati
]


def calculate_nadi_koota(groom_moon: Dict[str, Any], bride_moon: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nadi Koota (Max 8 points).
    Formula:
      NadiScore = 8 if Nadi_Groom != Nadi_Bride else 0.
    Flags basic Nadi Dosha when both share the same Nadi.
    """
    b_norm = normalize_moon_input(groom_moon, "groom_moon", require_sign=False, require_nakshatra=True)
    g_norm = normalize_moon_input(bride_moon, "bride_moon", require_sign=False, require_nakshatra=True)
    b_nak = b_norm["nakshatra_idx"]
    g_nak = g_norm["nakshatra_idx"]

    b_nadi = NAKSHATRA_TO_NADI[b_nak]
    g_nadi = NAKSHATRA_TO_NADI[g_nak]

    has_dosha = (b_nadi == g_nadi)
    score = 0.0 if has_dosha else 8.0

    return {
        "koot_code": "NADI",
        "koot_en": "Nadi",
        "koot_hi": "नाड़ी",
        "max": 8.0,
        "obtained": score,
        "groom_val": f"{b_nadi} ({NADI_NAMES_HI[b_nadi]})",
        "bride_val": f"{g_nadi} ({NADI_NAMES_HI[g_nadi]})",
        "groom_nadi": b_nadi,
        "bride_nadi": g_nadi,
        "has_dosha": has_dosha,
        "favorable": (score == 8.0),
        "rule_id": "NADI_CLASSICAL_EIGHT",
        "citation": "Muhurta Chintamani vivaha prakarana v. 37",
        "desc_en": "Genetic constitution, physiological vigor, progeny prospects and longevity.",
        "desc_hi": "अनुवांशिक स्वास्थ्य, नाड़ी ऊर्जा, संतान सुख व दीर्घायु सामंजस्य।"
    }


# ---------------------------------------------------------------------------
# AGGREGATOR FUNCTION: RUN ALL 8 KOOTAS INDEPENDENTLY
# ---------------------------------------------------------------------------
def calculate_all_eight_kootas(groom_moon: Dict[str, Any], bride_moon: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute all 8 Koota functions independently and return verified scores and audit metadata.
    Normalizes both inputs once with require_sign=True, require_nakshatra=True.
    """
    b_norm = normalize_moon_input(groom_moon, "groom_moon", require_sign=True, require_nakshatra=True)
    g_norm = normalize_moon_input(bride_moon, "bride_moon", require_sign=True, require_nakshatra=True)

    k1 = calculate_varna_koota(b_norm, g_norm)
    k2 = calculate_vashya_koota(b_norm, g_norm)
    k3 = calculate_tara_koota(b_norm, g_norm)
    k4 = calculate_yoni_koota(b_norm, g_norm)
    k5 = calculate_graha_maitri_koota(b_norm, g_norm)
    k6 = calculate_gana_koota(b_norm, g_norm)
    k7 = calculate_bhakoot_koota(b_norm, g_norm)
    k8 = calculate_nadi_koota(b_norm, g_norm)

    koots = [k1, k2, k3, k4, k5, k6, k7, k8]
    total_raw = sum(k["obtained"] for k in koots)

    return {
        "koots": koots,
        "total_raw": total_raw,
        "max_possible": 36.0,
        "percentage": round((total_raw / 36.0) * 100.0, 2)
    }
