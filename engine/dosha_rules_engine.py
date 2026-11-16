# -*- coding: utf-8 -*-
"""
Vedas Kundli - Classical Dosha Detection & Exception Engine
Covers:
1. Manglik / Kuja Dosha Engine (Lagna, Moon, Venus with 5 distinct output statuses and structured rule DB)
2. Nadi Dosha Exception Engine (Traceable classical exceptions with Rule IDs)
3. Bhakoot Dosha Exception Engine (Traceable classical cancellations with Rule IDs)
Never modifies raw Guna points silently.
"""

from typing import Dict, Any, List, Optional, Set
from engine.ashtakoota_engine import (
    NATURAL_RELATIONSHIPS, RASHI_LORDS, RASHI_TO_VARNA,
    NAKSHATRA_TO_NADI, NAKSHATRA_TO_GANA
)
from engine.ephemeris import RASHI_NAMES_EN, RASHI_NAMES_HI, NAKSHATRA_NAMES_EN, NAKSHATRA_NAMES_HI

# ---------------------------------------------------------------------------
# MANGAL / KUJA DOSHA CLASSICAL RULE DATABASE
# ---------------------------------------------------------------------------
# Classical references:
# BPHS: Brihat Parashara Hora Shastra Ch. 84
# MC: Muhurta Chintamani, Vivaha Prakarana
# DK: Devakeralam (Chandrakala Nadi)
# MM: Muhurta Martanda
# JP: Jataka Parijata

DEFAULT_MANGLIK_HOUSES = {1, 2, 4, 7, 8, 12}

HOUSE_NAMES_EN = {
    1: "1st (Lagna)", 2: "2nd (Dhana)", 4: "4th (Sukha)",
    7: "7th (Kalatra)", 8: "8th (Ayu/Mangalya)", 12: "12th (Vyaya/Shayya)"
}

HOUSE_NAMES_HI = {
    1: "प्रथम (लग्न)", 2: "द्वितीय (धन/कुटुंब)", 4: "चतुर्थ (सुख)",
    7: "सप्तम (जीवनसाथी)", 8: "अष्टम (मांगल्य/आयु)", 12: "द्वादश (शयन सुख)"
}


def are_planets_mutual_friends_or_same(p1: str, p2: str) -> bool:
    """Check if two planets are identical or mutually friendly."""
    if p1 == p2:
        return True
    p1_friends = NATURAL_RELATIONSHIPS.get(p1, {}).get("friends", set())
    p2_friends = NATURAL_RELATIONSHIPS.get(p2, {}).get("friends", set())
    return (p2 in p1_friends) and (p1 in p2_friends)


def evaluate_person_manglik(
    core_data: Dict[str, Any],
    manglik_houses: Optional[Set[int]] = None
) -> Dict[str, Any]:
    """
    Independent Manglik / Kuja Dosha Evaluation for a single chart.
    Calculates Mars placements from:
      1. Lagna (Marital persona & physical vitality)
      2. Moon (Emotional mind & psychological temperament)
      3. Venus (Karakatva for spouse & marital intimacy)

    Evaluates classical cancellation (Parihara) and mitigation rules.
    Outputs one of 5 distinct statuses:
      - 'Not present'
      - 'Present'
      - 'Partially mitigated'
      - 'Cancelled'
      - 'Inconclusive'
    """
    if manglik_houses is None:
        manglik_houses = DEFAULT_MANGLIK_HOUSES

    p_map = core_data.get("planet_by_id", {})
    meta = core_data.get("meta", {})
    lagna_sign_idx = (meta.get("lagna_sign_num", 1) - 1) % 12

    mars = p_map.get("Mars", {})
    moon = p_map.get("Moon", {})
    venus = p_map.get("Venus", {})
    jupiter = p_map.get("Jupiter", {})
    saturn = p_map.get("Saturn", {})

    if not mars:
        return {
            "status": "Inconclusive",
            "status_en": "Inconclusive (Mars data missing)",
            "status_hi": "अनिर्णायक (मंगल आंकड़े अनुपलब्ध)",
            "has_placement": False,
            "rules_applied": []
        }

    mars_sign_idx = int(mars.get("sign_idx", 0))
    mars_sign_num = mars_sign_idx + 1
    mars_deg = float(mars.get("deg_in_sign", 0.0))

    moon_sign_idx = int(moon.get("sign_idx", 0)) if moon else 0
    venus_sign_idx = int(venus.get("sign_idx", 0)) if venus else mars_sign_idx

    # House placements from the 3 reference points (1-indexed whole sign)
    h_lagna = ((mars_sign_idx - lagna_sign_idx + 12) % 12) + 1
    h_moon = ((mars_sign_idx - moon_sign_idx + 12) % 12) + 1
    h_venus = ((mars_sign_idx - venus_sign_idx + 12) % 12) + 1 if venus else None

    from_lagna = h_lagna in manglik_houses
    from_moon = h_moon in manglik_houses
    from_venus = (h_venus in manglik_houses) if h_venus is not None else False

    has_placement = from_lagna or from_moon or from_venus

    rules_applied: List[Dict[str, Any]] = []

    # If no placement in qualifying houses
    if not has_placement:
        return {
            "status": "Not present",
            "status_en": "Not present (Mars is in auspicious non-afflicting houses)",
            "status_hi": "अमंगल मुक्त (मंगल दोष कारक भावों में स्थित नहीं है)",
            "has_placement": False,
            "is_manglik": False,
            "is_cancelled": False,
            "is_mitigated": False,
            "from_lagna": False,
            "from_moon": False,
            "from_venus": False,
            "house_from_lagna": h_lagna,
            "house_from_moon": h_moon,
            "house_from_venus": h_venus,
            "mars_sign_en": RASHI_NAMES_EN[mars_sign_idx],
            "mars_sign_hi": RASHI_NAMES_HI[mars_sign_idx],
            "rules_applied": []
        }

    # Record detection rule
    rules_applied.append({
        "rule_id": "KUJA-DETECT-01",
        "name": "Kuja Placement in Sensitive Houses",
        "source": "Brihat Parashara Hora Shastra Ch. 84 v. 1 / Muhurta Chintamani",
        "condition": f"Mars in houses {sorted(list(manglik_houses))} from Lagna, Moon, or Venus",
        "evidence": f"Mars in House {h_lagna} from Lagna, House {h_moon} from Moon, House {h_venus} from Venus in {RASHI_NAMES_EN[mars_sign_idx]}",
        "applicable": True,
        "effect": "Detects Kuja Affliction"
    })

    cancellations: List[Dict[str, Any]] = []
    mitigations: List[Dict[str, Any]] = []

    # 1. Mars in Own Sign (Swakshetra: Aries or Scorpio) -> CANCELS
    if mars_sign_num in (1, 8):
        c_rule = {
            "rule_id": "KUJA-OWN",
            "name": "Swakshetra Mars Exemption (मेषे कुजे न दोषः स्यात्)",
            "source": "Brihat Parashara Hora Shastra Ch. 84 / Muhurta Martanda",
            "condition": "Mars in own sign (Aries or Scorpio)",
            "evidence": f"Mars is dignified in own sign {RASHI_NAMES_EN[mars_sign_idx]} ({RASHI_NAMES_HI[mars_sign_idx]})",
            "applicable": True,
            "effect": "Cancels"
        }
        cancellations.append(c_rule)
        rules_applied.append(c_rule)

    # 2. Mars in Exaltation (Uchcha: Capricorn) -> CANCELS
    if mars_sign_num == 10:
        c_rule = {
            "rule_id": "KUJA-UCHCHA",
            "name": "Exalted Mars in Capricorn (मकरे कुजे)",
            "source": "Devakeralam / Jataka Parijata Adhyaya 14",
            "condition": "Mars exalted in Capricorn (Makara)",
            "evidence": f"Mars is exalted in Capricorn at {mars_deg:.2f}°",
            "applicable": True,
            "effect": "Cancels"
        }
        cancellations.append(c_rule)
        rules_applied.append(c_rule)

    # 3. Mars in Debilitation (Neecha: Cancer) -> MITIGATES
    if mars_sign_num == 4:
        m_rule = {
            "rule_id": "KUJA-NEECHA",
            "name": "Debilitated Mars in Cancer (कर्क कुजे)",
            "source": "Phaladeepika / Jataka Parijata",
            "condition": "Mars debilitated in Cancer (Karka)",
            "evidence": f"Mars loses virulent malefic heat in oceanic watery Cancer ({mars_deg:.2f}°)",
            "applicable": True,
            "effect": "Mitigates"
        }
        mitigations.append(m_rule)
        rules_applied.append(m_rule)

    # 4. Independent Jupiter Conjunction -> CANCELS
    if jupiter:
        jup_sign_idx = int(jupiter.get("sign_idx", 0))
        if jup_sign_idx == mars_sign_idx:
            c_rule = {
                "rule_id": "KUJA-JUP-CONJ",
                "name": "Guru-Mangal Conjunction (गुरु-मंगल युति)",
                "source": "Brihat Parashara Hora Shastra Ch. 84 / Muhurta Chintamani",
                "condition": "Jupiter conjoins Mars in the same zodiac sign",
                "evidence": f"Jupiter and Mars both reside in {RASHI_NAMES_EN[mars_sign_idx]}",
                "applicable": True,
                "effect": "Cancels"
            }
            cancellations.append(c_rule)
            rules_applied.append(c_rule)

        # 5. Independent Jupiter Aspect (Drishti: 5th, 7th, 9th house distance) -> CANCELS
        jup_dist = ((mars_sign_idx - jup_sign_idx + 12) % 12) + 1
        if jup_dist in (5, 7, 9):
            c_rule = {
                "rule_id": "KUJA-JUP-ASPECT",
                "name": "Guru Drishti on Mars (गुरु की शुभ दृष्टि)",
                "source": "Brihat Parashara Hora Shastra / Phaladeepika",
                "condition": "Jupiter casts 5th, 7th, or 9th classical aspect onto Mars",
                "evidence": f"Jupiter aspects Mars with its {jup_dist}th house special aspect from {RASHI_NAMES_EN[jup_sign_idx]}",
                "applicable": True,
                "effect": "Cancels"
            }
            cancellations.append(c_rule)
            rules_applied.append(c_rule)

    # 6. Yogakaraka Lagna (Cancer and Leo Lagna) -> CANCELS
    if lagna_sign_idx in (3, 4):  # Cancer(3) or Leo(4)
        c_rule = {
            "rule_id": "KUJA-YOGAKARAKA",
            "name": "Yogakaraka Mars Exemption (योगकारक मंगल)",
            "source": "Brihat Parashara Hora Shastra Ch. 34 v. 38",
            "condition": "Native has Cancer or Leo Ascendant (Mars rules 5th+10th or 4th+9th)",
            "evidence": f"For {RASHI_NAMES_EN[lagna_sign_idx]} Lagna, Mars is supreme benefic Yogakaraka",
            "applicable": True,
            "effect": "Cancels"
        }
        cancellations.append(c_rule)
        rules_applied.append(c_rule)

    # 7. House-Specific Sign Exemptions -> CANCELS
    # 2nd house Mars in Gemini, Virgo, or Aries
    if h_lagna == 2 and mars_sign_num in (1, 3, 6):
        c_rule = {
            "rule_id": "KUJA-H2-EXEMPT",
            "name": "Second House Sign Exemption (द्वितीये कुजे)",
            "source": "Jyotirvidabharana / Devakeralam",
            "condition": "Mars in 2nd house in Gemini, Virgo, or Aries",
            "evidence": f"2nd house Mars in {RASHI_NAMES_EN[mars_sign_idx]} is scripturally exempt from family discord",
            "applicable": True,
            "effect": "Cancels"
        }
        cancellations.append(c_rule)
        rules_applied.append(c_rule)

    # 4th house Mars in Aries or Scorpio
    if h_lagna == 4 and mars_sign_num in (1, 8):
        c_rule = {
            "rule_id": "KUJA-H4-EXEMPT",
            "name": "Fourth House Swakshetra Exemption (तुरीये कुजे)",
            "source": "Brihat Parashara Hora Shastra",
            "condition": "Mars in 4th house in Aries or Scorpio",
            "evidence": f"4th house Mars is in swakshetra {RASHI_NAMES_EN[mars_sign_idx]}",
            "applicable": True,
            "effect": "Cancels"
        }
        cancellations.append(c_rule)
        rules_applied.append(c_rule)

    # 7th house Mars in Capricorn or Pisces
    if h_lagna == 7 and mars_sign_num in (10, 12):
        c_rule = {
            "rule_id": "KUJA-H7-EXEMPT",
            "name": "Seventh House Capricorn/Pisces Exemption (सप्तमे कुजे)",
            "source": "Muhurta Chintamani Vivaha Prakarana",
            "condition": "Mars in 7th house in Capricorn or Pisces",
            "evidence": f"7th house Mars in {RASHI_NAMES_EN[mars_sign_idx]} is classically mitigated from causing marital discord",
            "applicable": True,
            "effect": "Cancels"
        }
        cancellations.append(c_rule)
        rules_applied.append(c_rule)

    # 8th house Mars in Sagittarius or Pisces
    if h_lagna == 8 and mars_sign_num in (9, 12):
        c_rule = {
            "rule_id": "KUJA-H8-EXEMPT",
            "name": "Eighth House Jupiterian Sign Exemption (अष्टमे कुजे)",
            "source": "Brihat Parashara Hora Shastra",
            "condition": "Mars in 8th house in Sagittarius or Pisces",
            "evidence": f"8th house Mars in Jupiterian sign {RASHI_NAMES_EN[mars_sign_idx]} protects Mangalya",
            "applicable": True,
            "effect": "Cancels"
        }
        cancellations.append(c_rule)
        rules_applied.append(c_rule)

    # 12th house Mars in Taurus or Libra
    if h_lagna == 12 and mars_sign_num in (2, 7):
        c_rule = {
            "rule_id": "KUJA-H12-EXEMPT",
            "name": "Twelfth House Venusian Sign Exemption (व्यये कुजे)",
            "source": "Brihat Parashara Hora Shastra",
            "condition": "Mars in 12th house in Venusian sign Taurus or Libra",
            "evidence": f"12th house Mars in {RASHI_NAMES_EN[mars_sign_idx]} preserves conjugal bed comforts",
            "applicable": True,
            "effect": "Cancels"
        }
        cancellations.append(c_rule)
        rules_applied.append(c_rule)

    # 8. Benefic Influence (Venus / Moon conjunction in Kendra) -> MITIGATES
    if moon:
        if moon_sign_idx == mars_sign_idx:
            m_rule = {
                "rule_id": "KUJA-MOON-CONJ",
                "name": "Chandra-Mangal Yoga Mitigation (चन्द्र-मंगल योग)",
                "source": "Jataka Parijata / Saravali",
                "condition": "Moon conjoins Mars (Chandra-Mangal Yoga)",
                "evidence": f"Moon conjoins Mars in {RASHI_NAMES_EN[mars_sign_idx]} giving wealth and cooling fiery heat",
                "applicable": True,
                "effect": "Mitigates"
            }
            mitigations.append(m_rule)
            rules_applied.append(m_rule)

    # Determine final classical status
    if len(cancellations) > 0:
        final_status = "Cancelled"
        final_status_en = f"Cancelled (Neutralized by {len(cancellations)} classical Parihara rule{'s' if len(cancellations) > 1 else ''})"
        final_status_hi = f"परिहार मान्य — दोष निरस्त ({len(cancellations)} शास्त्रसम्मत परिहार सक्रिय)"
        is_manglik = False
        is_cancelled = True
        is_mitigated = True
    elif len(mitigations) > 0:
        final_status = "Partially mitigated"
        final_status_en = "Partially mitigated (Affliction moderated by benefic planetary factor)"
        final_status_hi = "आंशिक रूप से शांत (शुभ ग्रह प्रभाव द्वारा अनिष्टता में कमी)"
        is_manglik = True
        is_cancelled = False
        is_mitigated = True
    elif from_lagna and (from_moon or from_venus):
        final_status = "Present"
        final_status_en = "Present (Full Manglik from Lagna as well as Moon/Venus)"
        final_status_hi = "विद्यमान (लग्न तथा चन्द्र/शुक्र दोनों से पूर्ण मंगल दोष)"
        is_manglik = True
        is_cancelled = False
        is_mitigated = False
    else:
        final_status = "Present"
        final_status_en = "Present (Anshik / Partial Manglik from single focal point)"
        final_status_hi = "विद्यमान (एकल संदर्भ बिंदु से आंशिक मंगल दोष)"
        is_manglik = True
        is_cancelled = False
        is_mitigated = False

    return {
        "status": final_status,
        "status_en": final_status_en,
        "status_hi": final_status_hi,
        "has_placement": True,
        "is_manglik": is_manglik,
        "is_cancelled": is_cancelled,
        "is_mitigated": is_mitigated,
        "from_lagna": from_lagna,
        "from_moon": from_moon,
        "from_venus": from_venus,
        "house_from_lagna": h_lagna,
        "house_from_moon": h_moon,
        "house_from_venus": h_venus,
        "mars_sign_en": RASHI_NAMES_EN[mars_sign_idx],
        "mars_sign_hi": RASHI_NAMES_HI[mars_sign_idx],
        "mars_deg_in_sign": mars_deg,
        "cancellations": cancellations,
        "mitigations": mitigations,
        "rules_applied": rules_applied
    }


def evaluate_dosha_samya(groom_manglik: Dict[str, Any], bride_manglik: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate Kuja Dosha Samya (Mutual neutralization between couple).
    Rule: When both partners have Manglik Dosha, the dosha cancels itself out:
      "दम्पत्योर्जन्मकाले यदि भवति कुजस्तादृशो वै गुणानां..." (BPHS Ch. 84 v. 12).
    """
    g_m = groom_manglik.get("is_manglik", False)
    b_m = bride_manglik.get("is_manglik", False)
    g_c = groom_manglik.get("is_cancelled", False)
    b_c = bride_manglik.get("is_cancelled", False)

    rules = []

    if not g_m and not b_m:
        if g_c or b_c:
            compat = "Parihara Balanced"
            summary_en = "Harmonious: Kuja Dosha neutralized by individual classical Pariharas."
            summary_hi = "सद्भावपूर्ण सामंजस्य: शास्त्रसम्मत परिहार द्वारा कुज दोष निरस्त।"
        else:
            compat = "Clean"
            summary_en = "Both partners Non-Manglik: Perfectly free of Kuja Dosha."
            summary_hi = "वर व कन्या दोनों अमंगल मुक्त हैं: पूर्णतः निर्दोष व शुभ दांपत्य।"
    elif g_m and b_m:
        compat = "Neutralized"
        summary_en = "Both partners Manglik: Perfect Dosha Samya Neutralization (दोष साम्य परिहार)."
        summary_hi = "दोनों कुण्डलियों में कुज दोष साम्य होने से दोष स्वतः निष्प्रभावी [वृहत्पाराशर होराशास्त्र Ch. 84 v. 12]।"
        rules.append({
            "rule_id": "KUJA-DOSHA-SAMYA",
            "name": "Mutual Kuja Dosha Samya",
            "source": "Brihat Parashara Hora Shastra Ch. 84 v. 12",
            "condition": "Both Groom and Bride have active Kuja placements",
            "evidence": "Equal malefic placement creates harmonious balance and cancels mutual harm",
            "applicable": True,
            "effect": "Cancels"
        })
    else:
        mang_side = "Groom" if g_m else "Bride"
        compat = "Review"
        summary_en = f"One partner Manglik ({mang_side}): Requires classical remedial measures."
        summary_hi = f"एक पक्ष ({'वर' if mang_side == 'Groom' else 'कन्या'}) मांगलिक है: वैदिक शांति व परामर्श अपेक्षित।"

    return {
        "compat": compat,
        "summary_en": summary_en,
        "summary_hi": summary_hi,
        "groom_status": groom_manglik.get("status"),
        "bride_status": bride_manglik.get("status"),
        "rules_applied": rules
    }


# ---------------------------------------------------------------------------
# NADI DOSHA EXCEPTION ENGINE
# ---------------------------------------------------------------------------
# Traditional Nakshatras with classical Nadi exception support in traditional texts:
EXEMPT_NADI_NAKSHATRAS = {
    "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya",
    "Shravana", "Shatabhisha", "Uttara Bhadrapada"
}


def evaluate_nadi_exceptions(
    groom_moon: Dict[str, Any],
    bride_moon: Dict[str, Any],
    basic_nadi_score: float
) -> Dict[str, Any]:
    """
    Nadi Dosha Exception Engine.
    Detects same/different Nadi, same/different Nakshatra, same/different Rashi, same/different Pada.
    Applies classical exception rules with explicit Rule IDs.
    Raw score remains 0 if basic dosha is detected; detection and cancellation are returned separately.
    """
    b_nak_idx = int(groom_moon.get("nakshatra_idx", 0))
    g_nak_idx = int(bride_moon.get("nakshatra_idx", 0))
    b_rasi = int(groom_moon.get("sign_idx", 0))
    g_rasi = int(bride_moon.get("sign_idx", 0))
    b_pada = int(groom_moon.get("pada", 1))
    g_pada = int(bride_moon.get("pada", 1))

    b_nak_name = NAKSHATRA_NAMES_EN[b_nak_idx]
    g_nak_name = NAKSHATRA_NAMES_EN[g_nak_idx]

    b_nadi = NAKSHATRA_TO_NADI[b_nak_idx]
    g_nadi = NAKSHATRA_TO_NADI[g_nak_idx]

    same_nadi = (b_nadi == g_nadi)
    same_nakshatra = (b_nak_idx == g_nak_idx)
    same_rashi = (b_rasi == g_rasi)
    same_pada = (b_pada == g_pada)

    rules_evaluated: List[Dict[str, Any]] = []

    if not same_nadi:
        rule_record = {
            "rule_id": "NADI-002",
            "name": "Different Nadi Match",
            "source": "Muhurta Chintamani vivaha prakarana v. 37",
            "condition": "Nadi_Groom != Nadi_Bride",
            "evidence": f"Groom has {b_nadi} Nadi, Bride has {g_nadi} Nadi",
            "applicable": True,
            "effect": "No Dosha",
            "desc_en": "Horoscopes possess naturally complementary biological rhythms."
        }
        rules_evaluated.append(rule_record)
        return {
            "dosha_detected": False,
            "cancellation_status": "Not Applicable",
            "is_cancelled": False,
            "active_rule": rule_record,
            "rules_evaluated": rules_evaluated,
            "summary_en": "No Nadi Dosha: Different Nadis ensure genetic vigor and progeny welfare.",
            "summary_hi": "नाड़ी दोष नहीं: परस्पर भिन्न नाड़ी उत्तम वंश वृद्धि व स्वास्थ्यप्रद है।"
        }

    # Nadi Dosha is detected
    detect_rule = {
        "rule_id": "NADI-001",
        "name": "Same Nadi Affliction Detected",
        "source": "Muhurta Chintamani vivaha prakarana v. 37 / BPHS Ch. 81",
        "condition": "Nadi_Groom == Nadi_Bride",
        "evidence": f"Both partners share {b_nadi} Nadi",
        "applicable": True,
        "effect": "Dosha Detected",
        "desc_en": f"Both individuals belong to {b_nadi} Nadi, constituting classical Nadi Dosha."
    }
    rules_evaluated.append(detect_rule)

    cancellation_rules: List[Dict[str, Any]] = []

    # Exception Rule 1: Same Nakshatra, different Pada in same Rashi -> CANCELLED
    if same_nakshatra and same_rashi and not same_pada:
        c_rule = {
            "rule_id": "NADI-003",
            "name": "Same Nakshatra Different Pada Exemption",
            "source": "Muhurta Chintamani vivaha prakarana v. 37",
            "condition": "Same Nakshatra and same Rashi, but different Padas",
            "evidence": f"Nakshatra is {b_nak_name} for both, but Groom Pada is {b_pada} and Bride Pada is {g_pada}",
            "applicable": True,
            "effect": "Cancels",
            "desc_en": "Different Pada division channels planetary rays favorably, canceling Nadi Dosha (एकनक्षत्रे भिन्नचरणे शुभम्)।"
        }
        cancellation_rules.append(c_rule)
        rules_evaluated.append(c_rule)

    # Exception Rule 2: Same Rashi, different Nakshatras -> CANCELLED
    if same_rashi and not same_nakshatra:
        c_rule = {
            "rule_id": "NADI-004",
            "name": "Same Rashi Different Nakshatra Exemption",
            "source": "Muhurta Chintamani vivaha prakarana v. 37",
            "condition": "Same Rashi but different Nakshatras",
            "evidence": f"Both in {RASHI_NAMES_EN[b_rasi]}, but Groom is {b_nak_name} and Bride is {g_nak_name}",
            "applicable": True,
            "effect": "Cancels",
            "desc_en": "Common sign lordship harmonizes the biological clash (एकराशौ भिन्ननक्षत्रे नाड़ीदोषो न विद्यते)।"
        }
        cancellation_rules.append(c_rule)
        rules_evaluated.append(c_rule)

    # Exception Rule 3: Same Nakshatra bridging two different Rashis -> CANCELLED
    if same_nakshatra and not same_rashi:
        c_rule = {
            "rule_id": "NADI-005",
            "name": "Same Nakshatra Different Rashi Exemption",
            "source": "Brihat Parashara Hora Shastra / Narada Samhita",
            "condition": "Same Nakshatra divided across sign boundary (e.g., Krittika, Mrigashira)",
            "evidence": f"Same star {b_nak_name} in different Moon signs ({RASHI_NAMES_EN[b_rasi]} vs {RASHI_NAMES_EN[g_rasi]})",
            "applicable": True,
            "effect": "Cancels",
            "desc_en": "Transition of sign boundary neutralizes the Nadi obstruction."
        }
        cancellation_rules.append(c_rule)
        rules_evaluated.append(c_rule)

    # Exception Rule 4: Classical Exempt Nakshatras -> MITIGATES
    if b_nak_name in EXEMPT_NADI_NAKSHATRAS and g_nak_name in EXEMPT_NADI_NAKSHATRAS:
        m_rule = {
            "rule_id": "NADI-006",
            "name": "Classical Exempt Nakshatra Heritage",
            "source": "Narada Samhita / Atri Samhita",
            "condition": "Both Nakshatras belong to the classical exempt star catalogue",
            "evidence": f"Groom star {b_nak_name} and Bride star {g_nak_name} are traditionally exempted from fatal Nadi curse",
            "applicable": True,
            "effect": "Mitigates",
            "desc_en": "Specific stars are documented in classical Samhitas as immune from destructive Nadi consequences."
        }
        cancellation_rules.append(m_rule)
        rules_evaluated.append(m_rule)

    # Check Rashi Lord Friendship
    b_lord = RASHI_LORDS[b_rasi]
    g_lord = RASHI_LORDS[g_rasi]
    if are_planets_mutual_friends_or_same(b_lord, g_lord):
        f_rule = {
            "rule_id": "NADI-007",
            "name": "Friendly Rashi Lords Mitigation",
            "source": "Jyotish Darpana",
            "condition": "Moon sign lords are identical or mutual natural friends",
            "evidence": f"Lords {b_lord} and {g_lord} are in mutual harmony",
            "applicable": True,
            "effect": "Mitigates",
            "desc_en": "Planetary friendship provides substantial psychological and vital shielding."
        }
        rules_evaluated.append(f_rule)

    is_cancelled = any(r["effect"] == "Cancels" for r in cancellation_rules)
    is_mitigated = any(r["effect"] in ("Cancels", "Mitigates") for r in cancellation_rules)

    if is_cancelled:
        canc_status = "Cancelled"
        summary_en = f"Nadi Dosha Detected (0/8 raw), but Cancelled by classical Parihara ({cancellation_rules[0]['name']})."
        summary_hi = f"नाड़ी दोष उपस्थित (मूल अंक 0/8), किंतु शास्त्रसम्मत परिहार द्वारा निरस्त ({cancellation_rules[0]['name']})।"
    elif is_mitigated:
        canc_status = "Partially Mitigated"
        summary_en = "Nadi Dosha Detected (0/8 raw); partially mitigated by planetary factors. Classical remedies recommended."
        summary_hi = "नाड़ी दोष उपस्थित (मूल अंक 0/8); मित्र ग्रह प्रभाव से आंशिक शांत। वैदिक शांति अनुशंसित।"
    else:
        canc_status = "Not Applicable"
        summary_en = "Nadi Dosha Active (0/8 raw). No classical cancellation applies; Mahamrityunjaya japa & gold donation advised."
        summary_hi = "गंभीर नाड़ी दोष उपस्थित (मूल अंक 0/8)। कोई परिहार लागू नहीं; महामृत्युंजय जप एवं शांति अनुष्ठान अनिवार्य।"

    return {
        "dosha_detected": True,
        "cancellation_status": canc_status,
        "is_cancelled": is_cancelled,
        "is_mitigated": is_mitigated,
        "same_nakshatra": same_nakshatra,
        "same_rashi": same_rashi,
        "same_pada": same_pada,
        "active_cancellations": cancellation_rules,
        "rules_evaluated": rules_evaluated,
        "summary_en": summary_en,
        "summary_hi": summary_hi
    }


# ---------------------------------------------------------------------------
# BHAKOOT DOSHA EXCEPTION ENGINE
# ---------------------------------------------------------------------------
def evaluate_bhakoot_exceptions(
    groom_moon: Dict[str, Any],
    bride_moon: Dict[str, Any],
    has_basic_dosha: bool
) -> Dict[str, Any]:
    """
    Bhakoot Dosha Exception Engine.
    Evaluates 2/12 (Dwirdwadasha), 5/9 (Navam-Pancham), 6/8 (Shadashtaka).
    Tests for classical cancellations:
      - Eka-Adhipatya (Same Moon sign lord, e.g. Aries-Scorpio, Taurus-Libra)
      - Mutual friendly Moon sign lords
      - Auspicious Shadashtaka (Maitra Shadashtaka) vs Inauspicious (Mrityu Shadashtaka)
    Returns:
      Bhakoot Dosha: Detected / Not detected
      Bhakoot Cancellation: Applicable / Not applicable / Unverified
    """
    b_rasi = int(groom_moon.get("sign_idx", 0))
    g_rasi = int(bride_moon.get("sign_idx", 0))

    dist_groom_to_bride = ((g_rasi - b_rasi + 12) % 12) + 1
    dist_bride_to_groom = ((b_rasi - g_rasi + 12) % 12) + 1
    pair_label = f"{dist_groom_to_bride}/{dist_bride_to_groom}"

    b_lord = RASHI_LORDS[b_rasi]
    g_lord = RASHI_LORDS[g_rasi]

    rules_evaluated: List[Dict[str, Any]] = []

    if not has_basic_dosha:
        r_rec = {
            "rule_id": "BHAKOOT-000",
            "name": "Auspicious Bhakoot Geometry",
            "source": "Muhurta Chintamani vivaha prakarana v. 32",
            "condition": "Moon signs in 1/1, 3/11, 4/10, or 7/7 relationship",
            "evidence": f"Moon sign distance is {pair_label} ({RASHI_NAMES_EN[b_rasi]} vs {RASHI_NAMES_EN[g_rasi]})",
            "applicable": True,
            "effect": "No Dosha",
            "desc_en": "Mutual planetary houses encourage harmony, wealth and flourishing domestic life."
        }
        rules_evaluated.append(r_rec)
        return {
            "dosha_detected": False,
            "cancellation_status": "Not Applicable",
            "is_cancelled": False,
            "pair_label": pair_label,
            "rules_evaluated": rules_evaluated,
            "summary_en": f"Auspicious Bhakoot Harmony ({pair_label}): Free of Bhakoot Dosha.",
            "summary_hi": f"शुभ भकूट अनुकूलता ({pair_label}): भकूट दोष से मुक्त।"
        }

    # Basic Bhakoot Dosha is detected
    d_rule = {
        "rule_id": "BHAKOOT-001",
        "name": f"Bhakoot Affliction Detected ({pair_label})",
        "source": "Muhurta Chintamani vivaha prakarana v. 32",
        "condition": "Moon signs in 2/12, 5/9, or 6/8 distance",
        "evidence": f"Relative distances {dist_groom_to_bride} and {dist_bride_to_groom} form inauspicious angle",
        "applicable": True,
        "effect": "Dosha Detected",
        "desc_en": f"Relationship {pair_label} classically indicates financial drain (2/12), progeny distress (5/9), or health friction (6/8)."
    }
    rules_evaluated.append(d_rule)

    cancellations: List[Dict[str, Any]] = []

    # Rule 1: Eka-Adhipatya (Same Moon Sign Lord) -> CANCELS
    # E.g. Aries and Scorpio (Mars), Taurus and Libra (Venus)
    if b_lord == g_lord:
        c_rule = {
            "rule_id": "BHAKOOT-002",
            "name": "Eka-Adhipatya Parihara (एक ही राशि स्वामी)",
            "source": "Muhurta Chintamani vivaha prakarana v. 32 / BPHS Ch. 81",
            "condition": "Both Moon signs share the exact same planetary lord",
            "evidence": f"Both {RASHI_NAMES_EN[b_rasi]} and {RASHI_NAMES_EN[g_rasi]} are owned by {b_lord}",
            "applicable": True,
            "effect": "Cancels",
            "desc_en": "Since one single planet commands both minds, Bhakoot Dosha is completely nullified (एकाधिपत्ये दोषो न विद्यते)।"
        }
        cancellations.append(c_rule)
        rules_evaluated.append(c_rule)

    # Rule 2: Mutual Friendly Lords -> CANCELS
    # E.g. Sun and Jupiter (Leo 5/9 Sagittarius or Pisces), Moon and Mars (Cancer-Scorpio), etc.
    elif are_planets_mutual_friends_or_same(b_lord, g_lord):
        c_rule = {
            "rule_id": "BHAKOOT-003",
            "name": "Maitri Parihara (राशि स्वामियों की मित्रता)",
            "source": "Muhurta Chintamani vivaha prakarana v. 32",
            "condition": "Rashi lords are mutual natural friends",
            "evidence": f"Lords {b_lord} and {g_lord} share reciprocal planetary friendship",
            "applicable": True,
            "effect": "Cancels",
            "desc_en": "Mutual planetary friendship shields the domestic sphere against Bhakoot friction."
        }
        cancellations.append(c_rule)
        rules_evaluated.append(c_rule)

    # Rule 3: Maitra Shadashtaka (Favorable 6/8 pairs)
    if {dist_groom_to_bride, dist_bride_to_groom} == {6, 8}:
        # Friendly 6/8 pairs: Aries-Scorpio, Gemini-Capricorn, Leo-Pisces
        maitra_pairs = {(0, 7), (7, 0), (2, 9), (9, 2), (4, 11), (11, 4)}
        if (b_rasi, g_rasi) in maitra_pairs:
            m_rule = {
                "rule_id": "BHAKOOT-005",
                "name": "Maitra Shadashtaka Exemption (मैत्र षडाष्टक)",
                "source": "Jataka Parijata / Muhurta Chintamani",
                "condition": "6/8 relationship occurs between signs with auspicious harmony (Maitra Shadashtaka)",
                "evidence": f"{RASHI_NAMES_EN[b_rasi]} and {RASHI_NAMES_EN[g_rasi]} form documented Maitra Shadashtaka",
                "applicable": True,
                "effect": "Cancels",
                "desc_en": "Classified as auspicious Preeti Shadashtaka rather than fatal Mrityu Shadashtaka."
            }
            cancellations.append(m_rule)
            rules_evaluated.append(m_rule)

    is_cancelled = len(cancellations) > 0

    if is_cancelled:
        canc_status = "Applicable"
        summary_en = f"Bhakoot Dosha Detected ({pair_label}), but Cancelled by classical Parihara: {cancellations[0]['name']}."
        summary_hi = f"भकूट दोष उपस्थित ({pair_label}), किंतु शास्त्रसम्मत परिहार मान्य: {cancellations[0]['name']}।"
    else:
        canc_status = "Not applicable"
        summary_en = f"Bhakoot Dosha Active ({pair_label}): No classical cancellation applies."
        summary_hi = f"भकूट दोष प्रभावी ({pair_label}): कोई शास्त्रीय परिहार लागू नहीं होता।"

    return {
        "dosha_detected": True,
        "cancellation_status": canc_status,
        "is_cancelled": is_cancelled,
        "pair_label": pair_label,
        "active_cancellations": cancellations,
        "rules_evaluated": rules_evaluated,
        "summary_en": summary_en,
        "summary_hi": summary_hi
    }
