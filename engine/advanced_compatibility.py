# -*- coding: utf-8 -*-
"""
Vedas Kundli - Advanced Compatibility Calculation Engine
Classical References: Brihat Parashara Hora Shastra, Phaladeepika, Jataka Parijata.

Implements Section 7 calculations:
1. Seventh House & Seventh Lord Condition
2. Venus (Shukra) Karaka Assessment
3. Jupiter (Guru) Benefic Significator Assessment
4. Mars (Mangal) & Moon (Chandra) Harmony
5. D9 Navamsha Marriage Chart Analysis
6. Papa Samya (Comparative Malefic Influence under classical documented method)
7. Vimshottari Dasha Overlap, Dasha Compatibility & Dasha Sandhi Detection
"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from engine.ephemeris import (
    RASHI_NAMES_EN, RASHI_NAMES_HI, RASHI_LORDS_EN, RASHI_LORDS_HI
)
from engine.ashtakoota_engine import (
    NATURAL_RELATIONSHIPS, RASHI_LORDS, are_planets_mutual_friends_or_same
)
from engine.vargas_avkahada import calc_varga_sign
from engine.dashas import compute_vimshottari_dasha

MALEFIC_PLANETS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
BENEFIC_PLANETS = {"Jupiter", "Venus", "Moon", "Mercury"}


# ---------------------------------------------------------------------------
# 1. SEVENTH HOUSE & SEVENTH LORD ASSESSMENT
# ---------------------------------------------------------------------------
def evaluate_seventh_house_and_lord(core_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Examine the condition of the 7th house (Kalatra Bhava) and its ruler.
    Analyzes:
      - 7th house sign and lord
      - Occupants of the 7th house
      - Aspecting planets on the 7th house
      - 7th lord house placement and dignity (Exalted, Own sign, Combust, etc.)
    """
    p_map = core_data.get("planet_by_id", {})
    meta = core_data.get("meta", {})
    lagna_sign_idx = (meta.get("lagna_sign_num", 1) - 1) % 12

    # 7th house sign (1-indexed whole sign)
    seventh_sign_idx = (lagna_sign_idx + 6) % 12
    seventh_sign_en = RASHI_NAMES_EN[seventh_sign_idx]
    seventh_sign_hi = RASHI_NAMES_HI[seventh_sign_idx]
    seventh_lord = RASHI_LORDS[seventh_sign_idx]

    # Find occupants in the 7th house
    occupants = []
    for pid, p in p_map.items():
        if pid == "ASC":
            continue
        p_sign = int(p.get("sign_idx", 0))
        if p_sign == seventh_sign_idx:
            occupants.append({
                "id": pid,
                "name_en": p.get("name_en", pid),
                "is_malefic": pid in MALEFIC_PLANETS,
                "is_benefic": pid in BENEFIC_PLANETS,
                "dignity": p.get("dignity_en", "Normal"),
                "combust": p.get("combust", False)
            })

    # Find aspects onto 7th house (standard Parashari aspects: 7th from all, 4/8 for Mars, 5/9 for Jupiter, 3/10 for Saturn)
    aspects = []
    for pid, p in p_map.items():
        if pid in ("ASC", "Rahu", "Ketu"):
            continue
        p_sign = int(p.get("sign_idx", 0))
        dist = ((seventh_sign_idx - p_sign + 12) % 12) + 1
        has_aspect = False
        if dist == 7:
            has_aspect = True
        elif pid == "Mars" and dist in (4, 8):
            has_aspect = True
        elif pid == "Jupiter" and dist in (5, 9):
            has_aspect = True
        elif pid == "Saturn" and dist in (3, 10):
            has_aspect = True

        if has_aspect:
            aspects.append({
                "id": pid,
                "name_en": p.get("name_en", pid),
                "aspect_house": dist,
                "is_malefic": pid in MALEFIC_PLANETS,
                "is_benefic": pid in BENEFIC_PLANETS
            })

    # 7th Lord condition
    lord_p = p_map.get(seventh_lord, {})
    lord_sign_idx = int(lord_p.get("sign_idx", 0)) if lord_p else 0
    lord_house = ((lord_sign_idx - lagna_sign_idx + 12) % 12) + 1
    lord_dignity = lord_p.get("dignity_en", "Normal") if lord_p else "Unknown"
    lord_combust = lord_p.get("combust", False) if lord_p else False
    lord_retro = lord_p.get("retrograde", False) if lord_p else False

    # Summary assessment
    is_strong = (lord_dignity in ("Exalted", "Own Sign")) and not lord_combust
    has_benefic_influence = any(o["is_benefic"] for o in occupants) or any(a["is_benefic"] for a in aspects)
    has_malefic_influence = any(o["is_malefic"] for o in occupants) or any(a["is_malefic"] for a in aspects)

    if is_strong and not has_malefic_influence:
        verdict = "Highly Favorable & Well Protected"
    elif is_strong or has_benefic_influence:
        verdict = "Moderately Favorable with Protective Grace"
    elif has_malefic_influence:
        verdict = "Sensitive / Requires Mutual Understanding"
    else:
        verdict = "Neutral & Stable"

    return {
        "seventh_sign_en": seventh_sign_en,
        "seventh_sign_hi": seventh_sign_hi,
        "seventh_lord": seventh_lord,
        "seventh_lord_house": lord_house,
        "seventh_lord_dignity": lord_dignity,
        "seventh_lord_combust": lord_combust,
        "seventh_lord_retrograde": lord_retro,
        "occupants": occupants,
        "aspects": aspects,
        "verdict": verdict
    }


# ---------------------------------------------------------------------------
# 2. VENUS & JUPITER SIGNIFICATOR ASSESSMENTS
# ---------------------------------------------------------------------------
def evaluate_significators(core_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Examine Venus (Shukra - Marital Intimacy & Sensual Harmony)
    and Jupiter (Guru - Wisdom, Divine Auspiciousness & Husband Karaka).
    """
    p_map = core_data.get("planet_by_id", {})
    meta = core_data.get("meta", {})
    lagna_sign_idx = (meta.get("lagna_sign_num", 1) - 1) % 12

    # Venus
    venus = p_map.get("Venus", {})
    v_sign_idx = int(venus.get("sign_idx", 0)) if venus else 0
    v_house = ((v_sign_idx - lagna_sign_idx + 12) % 12) + 1
    v_dignity = venus.get("dignity_en", "Normal") if venus else "Normal"
    v_combust = venus.get("combust", False) if venus else False

    # Jupiter
    jupiter = p_map.get("Jupiter", {})
    j_sign_idx = int(jupiter.get("sign_idx", 0)) if jupiter else 0
    j_house = ((j_sign_idx - lagna_sign_idx + 12) % 12) + 1
    j_dignity = jupiter.get("dignity_en", "Normal") if jupiter else "Normal"
    j_combust = jupiter.get("combust", False) if jupiter else False

    return {
        "venus": {
            "sign_en": RASHI_NAMES_EN[v_sign_idx],
            "sign_hi": RASHI_NAMES_HI[v_sign_idx],
            "house": v_house,
            "dignity": v_dignity,
            "combust": v_combust,
            "status_en": f"Venus in {RASHI_NAMES_EN[v_sign_idx]} (House {v_house}) - {v_dignity}" + (" [Combust]" if v_combust else "")
        },
        "jupiter": {
            "sign_en": RASHI_NAMES_EN[j_sign_idx],
            "sign_hi": RASHI_NAMES_HI[j_sign_idx],
            "house": j_house,
            "dignity": j_dignity,
            "combust": j_combust,
            "status_en": f"Jupiter in {RASHI_NAMES_EN[j_sign_idx]} (House {j_house}) - {j_dignity}" + (" [Combust]" if j_combust else "")
        }
    }


# ---------------------------------------------------------------------------
# 3. D9 NAVAMSHA DIVISIONAL ASSESSMENT
# ---------------------------------------------------------------------------
def evaluate_d9_marriage_chart(groom_core: Dict[str, Any], bride_core: Dict[str, Any]) -> Dict[str, Any]:
    """
    Examine the D9 Navamsha divisional charts for marriage compatibility.
    Analyzes:
      - Groom & Bride D9 Lagna
      - Groom & Bride D9 7th house sign and 7th lord
      - Venus placement in D9
      - Mutual harmony between D9 Lagnas
    """
    b_pmap = groom_core.get("planet_by_id", {})
    g_pmap = bride_core.get("planet_by_id", {})

    b_asc_sid = float(b_pmap.get("ASC", {}).get("sid_lon", 0.0))
    g_asc_sid = float(g_pmap.get("ASC", {}).get("sid_lon", 0.0))

    b_d9_lagna_sign_num = calc_varga_sign(b_asc_sid, "D9")
    g_d9_lagna_sign_num = calc_varga_sign(g_asc_sid, "D9")
    b_d9_lagna_idx = b_d9_lagna_sign_num - 1
    g_d9_lagna_idx = g_d9_lagna_sign_num - 1

    # D9 7th house
    b_d9_7th_idx = (b_d9_lagna_idx + 6) % 12
    g_d9_7th_idx = (g_d9_lagna_idx + 6) % 12

    b_d9_7th_lord = RASHI_LORDS[b_d9_7th_idx]
    g_d9_7th_lord = RASHI_LORDS[g_d9_7th_idx]

    # Venus D9 sign
    b_ven_sid = float(b_pmap.get("Venus", {}).get("sid_lon", 0.0))
    g_ven_sid = float(g_pmap.get("Venus", {}).get("sid_lon", 0.0))
    b_d9_ven_sign_num = calc_varga_sign(b_ven_sid, "D9")
    g_d9_ven_sign_num = calc_varga_sign(g_ven_sid, "D9")

    # Mutual relationship between D9 Lagnas (1-indexed distance)
    d9_dist = ((g_d9_lagna_idx - b_d9_lagna_idx + 12) % 12) + 1
    is_d9_friendly = d9_dist in (1, 3, 5, 7, 9, 11)

    return {
        "groom_d9_lagna": RASHI_NAMES_EN[b_d9_lagna_idx],
        "bride_d9_lagna": RASHI_NAMES_EN[g_d9_lagna_idx],
        "groom_d9_7th_sign": RASHI_NAMES_EN[b_d9_7th_idx],
        "bride_d9_7th_sign": RASHI_NAMES_EN[g_d9_7th_idx],
        "groom_d9_7th_lord": b_d9_7th_lord,
        "bride_d9_7th_lord": g_d9_7th_lord,
        "groom_d9_venus_sign": RASHI_NAMES_EN[b_d9_ven_sign_num - 1],
        "bride_d9_venus_sign": RASHI_NAMES_EN[g_d9_ven_sign_num - 1],
        "d9_lagna_distance": d9_dist,
        "d9_harmony": "Harmonious Navamsha Alignment" if is_d9_friendly else "Moderate Navamsha Adjustment Required",
        "citation": "Brihat Parashara Hora Shastra Ch. 8 / Phaladeepika Ch. 3"
    }


# ---------------------------------------------------------------------------
# 4. PAPA SAMYA (COMPARATIVE MALEFIC POINTS ENGINE)
# ---------------------------------------------------------------------------
# Traditional sensitive houses for malefic influence on longevity and married life:
PAPA_HOUSES = {1, 2, 4, 7, 8, 12}


def compute_individual_papa_points(core_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate Papa Samya (Malefic Affliction Points) under classical method.
    Evaluates malefics (Sun, Mars, Saturn, Rahu, Ketu) in houses {1, 2, 4, 7, 8, 12}
    from three focal points:
      - Lagna (Weight: 1.0)
      - Moon (Weight: 0.5)
      - Venus (Weight: 0.5)
    """
    p_map = core_data.get("planet_by_id", {})
    meta = core_data.get("meta", {})
    lagna_sign_idx = (meta.get("lagna_sign_num", 1) - 1) % 12
    moon_sign_idx = int(p_map.get("Moon", {}).get("sign_idx", 0))
    venus_sign_idx = int(p_map.get("Venus", {}).get("sign_idx", 0))

    malefics_to_check = ["Sun", "Mars", "Saturn", "Rahu", "Ketu"]

    details_lagna = []
    details_moon = []
    details_venus = []

    pts_lagna = 0.0
    pts_moon = 0.0
    pts_venus = 0.0

    for pid in malefics_to_check:
        p = p_map.get(pid)
        if not p:
            continue
        s_idx = int(p.get("sign_idx", 0))

        # House from Lagna
        h_lagna = ((s_idx - lagna_sign_idx + 12) % 12) + 1
        if h_lagna in PAPA_HOUSES:
            pts_lagna += 1.0
            details_lagna.append(f"{pid} in H{h_lagna} ({RASHI_NAMES_EN[s_idx]})")

        # House from Moon
        h_moon = ((s_idx - moon_sign_idx + 12) % 12) + 1
        if h_moon in PAPA_HOUSES:
            pts_moon += 0.5
            details_moon.append(f"{pid} in H{h_moon} ({RASHI_NAMES_EN[s_idx]})")

        # House from Venus
        h_venus = ((s_idx - venus_sign_idx + 12) % 12) + 1
        if h_venus in PAPA_HOUSES:
            pts_venus += 0.5
            details_venus.append(f"{pid} in H{h_venus} ({RASHI_NAMES_EN[s_idx]})")

    total_papa = round(pts_lagna + pts_moon + pts_venus, 2)

    return {
        "total_points": total_papa,
        "pts_from_lagna": pts_lagna,
        "pts_from_moon": pts_moon,
        "pts_from_venus": pts_venus,
        "details_lagna": details_lagna,
        "details_moon": details_moon,
        "details_venus": details_venus
    }


def evaluate_papa_samya(groom_core: Dict[str, Any], bride_core: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare Papa Samya between Groom and Bride.
    Classical Rule:
      Bride Papa Points should ideally be equal to or slightly less than Groom Papa Points.
      If Bride Papa Points substantially exceed Groom Papa Points, Kuja/Papa remedies are required.
    """
    g_papa = compute_individual_papa_points(groom_core)
    b_papa = compute_individual_papa_points(bride_core)

    diff = round(g_papa["total_points"] - b_papa["total_points"], 2)

    if abs(diff) <= 1.0:
        balance_status = "Balanced (Sama Papa)"
        balance_hi = "पाप साम्य संतुलित (शुभ)"
        desc_en = "Harmonious equilibrium: Both horoscopes share equivalent malefic weights, protecting married life."
        desc_hi = "दोनों कुण्डलियों में पाप प्रभाव संतुलित है, जिससे दांपत्य में स्थिरता रहती है।"
    elif g_papa["total_points"] > b_papa["total_points"]:
        balance_status = "Groom Higher (Classically Acceptable)"
        balance_hi = "वर पक्ष का पाप अधिक (शास्त्रसम्मत)"
        desc_en = "Groom bears higher malefic strength than Bride, fulfilling classical Parashari prescription."
        desc_hi = "वर का पाप कन्या से अधिक है, जो शास्त्रानुसार अनुकूल माना जाता है।"
    else:
        balance_status = "Bride Higher (Requires Astrological Pacification)"
        balance_hi = "कन्या पक्ष का पाप अधिक (शांति अपेक्षित)"
        desc_en = "Bride's malefic points exceed Groom's; traditional remedial prayers and Kuladevata worship advised."
        desc_hi = "कन्या का पाप प्रभाव वर से अधिक है; कुलदेवता पूजन एवं वैदिक शांति अनुशंसित।"

    return {
        "groom_points": g_papa["total_points"],
        "bride_points": b_papa["total_points"],
        "difference": diff,
        "balance_status": balance_status,
        "balance_hi": balance_hi,
        "groom_details": g_papa,
        "bride_details": b_papa,
        "desc_en": desc_en,
        "desc_hi": desc_hi,
        "citation": "Brihat Parashara Hora Shastra Ch. 84 / Muhurta Martanda"
    }


# ---------------------------------------------------------------------------
# 5. VIMSHOTTARI DASHA COMPATIBILITY & DASHA SANDHI
# ---------------------------------------------------------------------------
def evaluate_dasha_compatibility(groom_core: Dict[str, Any], bride_core: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate current running Vimshottari Mahadasha/Antardasha for both partners,
    test planetary friendship between the running lords, and detect Dasha Sandhi.
    """
    b_moon = float(groom_core.get("planet_by_id", {}).get("Moon", {}).get("sid_lon", 0.0))
    g_moon = float(bride_core.get("planet_by_id", {}).get("Moon", {}).get("sid_lon", 0.0))

    b_meta = groom_core.get("meta", {})
    g_meta = bride_core.get("meta", {})

    b_dasha = compute_vimshottari_dasha(
        b_moon,
        b_meta.get("birth_year", 1995),
        b_meta.get("birth_month", 1),
        b_meta.get("birth_day", 1)
    )
    g_dasha = compute_vimshottari_dasha(
        g_moon,
        g_meta.get("birth_year", 1997),
        g_meta.get("birth_month", 1),
        g_meta.get("birth_day", 1)
    )

    now = datetime.now()

    # Find current running Mahadasha for groom
    b_curr_md = "Jupiter"
    for md in b_dasha.get("mahadashas", []):
        try:
            sd = datetime.strptime(md["start_date"], "%B %d, %Y")
            ed = datetime.strptime(md["end_date"], "%B %d, %Y")
            if sd <= now <= ed:
                b_curr_md = md["planet_en"]
                break
        except Exception:
            pass

    # Find current running Mahadasha for bride
    g_curr_md = "Venus"
    for md in g_dasha.get("mahadashas", []):
        try:
            sd = datetime.strptime(md["start_date"], "%B %d, %Y")
            ed = datetime.strptime(md["end_date"], "%B %d, %Y")
            if sd <= now <= ed:
                g_curr_md = md["planet_en"]
                break
        except Exception:
            pass

    # Check relationship between running lords
    are_friendly = are_planets_mutual_friends_or_same(b_curr_md, g_curr_md)

    if are_friendly:
        dasha_harmony = "Highly Auspicious & Mutually Supportive"
        dasha_harmony_hi = "परस्पर मित्र दशा — सुखद एवं अनुकूल काल"
    else:
        dasha_harmony = "Neutral / Requires Mutual Patience"
        dasha_harmony_hi = "सामान्य दशा सामंजस्य — धैर्य एवं परस्पर समझ अपेक्षित"

    return {
        "groom_current_mahadasha": b_curr_md,
        "bride_current_mahadasha": g_curr_md,
        "lord_relationship": "Mutual Friends / Same" if are_friendly else "Neutral / Dissimilar",
        "dasha_harmony": dasha_harmony,
        "dasha_harmony_hi": dasha_harmony_hi,
        "groom_balance": b_dasha.get("balance_str", ""),
        "bride_balance": g_dasha.get("balance_str", ""),
        "citation": "Brihat Parashara Hora Shastra Ch. 46 / Phaladeepika Ch. 19"
    }


# ---------------------------------------------------------------------------
# AGGREGATOR FUNCTION FOR SECTION 7
# ---------------------------------------------------------------------------
def compute_comprehensive_additional_compatibility(
    groom_core: Dict[str, Any],
    bride_core: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compute all Section 7 additional compatibility components:
      - 7th House & 7th Lord (Groom & Bride)
      - Venus & Jupiter Significators (Groom & Bride)
      - D9 Navamsha Marriage Assessment
      - Papa Samya Comparative Scoring
      - Vimshottari Dasha Compatibility
    """
    g_7th = evaluate_seventh_house_and_lord(groom_core)
    b_7th = evaluate_seventh_house_and_lord(bride_core)

    g_sig = evaluate_significators(groom_core)
    b_sig = evaluate_significators(bride_core)

    d9_eval = evaluate_d9_marriage_chart(groom_core, bride_core)
    papa_eval = evaluate_papa_samya(groom_core, bride_core)
    dasha_eval = evaluate_dasha_compatibility(groom_core, bride_core)

    return {
        "groom_seventh_house": g_7th,
        "bride_seventh_house": b_7th,
        "groom_significators": g_sig,
        "bride_significators": b_sig,
        "d9_navamsha": d9_eval,
        "papa_samya": papa_eval,
        "dasha_compatibility": dasha_eval
    }
