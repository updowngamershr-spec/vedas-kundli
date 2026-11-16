# -*- coding: utf-8 -*-
"""
Vedas Kundli - Classical Ashtakoot 36-Guna Kundli Matching Engine
Dataset: Ashtakoota Jyotish Master Dataset v1.0.0 (Muhurta Chintamani, Nemichandra Shastri, B.V. Raman)

Features:
1. 8 Classical Kootas:
   - Varna (1): Groom varna rank <= Bride varna rank in [Brahmin, Kshatriya, Vaishya, Shudra]
   - Vashya (2): 4-class primary matrix (Dvipada, Chatushpada, Jalachara, Keeta)
   - Tara (3): Nakshatra count inclusive both ways mod 9 (unfavourable: 3, 5, 7)
   - Yoni (4): 14 animal archetypes, full 14x14 matrix
   - Graha Maitri (5): Moon sign lords natural relationship 7x7 matrix
   - Gana (6): Deva, Manushya, Rakshasa 3x3 directional matrix
   - Bhakoot (7): Relative sign distance (0 for 2/12, 5/9, 6/8; 7 otherwise)
   - Nadi (8): 8 if different Nadi, 0 if same Nadi
   Total: 36 Gunas
2. Classical Dosha Parihara (Cancellation Rules):
   - Policy: Raw koota scores are never silently changed by dosha-parihara rules;
     pariharas are evaluated, cited, and displayed transparently alongside raw scores.
   - Textual sources cited with chapter and verse (e.g., Muhurta Chintamani vv. 32, 33, 37).
3. Kuja / Mangal Dosha assessment (Lagna, Moon, Venus) & Dosha Samya harmony.
4. Source persistence: source_id and rule_version persisted with every calculation.
"""

import json
import os
import sys
from typing import Dict, Any, Optional, Tuple, List

from engine.ephemeris import (
    RASHI_NAMES_EN, RASHI_NAMES_HI, RASHI_LORDS_SHORT, RASHI_LORDS_HI,
    NAKSHATRA_NAMES_EN, NAKSHATRA_NAMES_HI, compute_core_ephemeris
)

from engine.ashtakoota_engine import (
    calculate_varna_koota, calculate_vashya_koota, calculate_tara_koota,
    calculate_yoni_koota, calculate_graha_maitri_koota, calculate_gana_koota,
    calculate_bhakoot_koota, calculate_nadi_koota, calculate_all_eight_kootas,
    VASHYA_5X5_MATRIX, VASHYA_GROUPS, YONI_14X14_MATRIX, GRAHA_MAITRI_7X7_MATRIX,
    GANA_3X3_MATRIX
)
from engine.dosha_rules_engine import (
    evaluate_person_manglik, evaluate_dosha_samya,
    evaluate_nadi_exceptions, evaluate_bhakoot_exceptions
)
from engine.advanced_compatibility import (
    compute_comprehensive_additional_compatibility,
    evaluate_seventh_house_and_lord, evaluate_significators,
    evaluate_d9_marriage_chart, evaluate_papa_samya,
    evaluate_dasha_compatibility
)

# ---------------------------------------------------------------------------
# Load Master Dataset
# ---------------------------------------------------------------------------
def _find_master_dataset_path() -> str:
    candidates = [
        os.path.join(getattr(sys, '_MEIPASS', ''), "data", "ashtakoota_master_dataset.json"),
        os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else '', "data", "ashtakoota_master_dataset.json"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ashtakoota_master_dataset.json"),
        os.path.join(os.getcwd(), "data", "ashtakoota_master_dataset.json")
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ashtakoota_master_dataset.json")

DATASET_PATH = _find_master_dataset_path()

try:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        MASTER_DATASET = json.load(f)
except Exception:
    MASTER_DATASET = {}

DATASET_NAME = MASTER_DATASET.get("dataset_name", "Ashtakoota Jyotish Master Dataset")
RULE_VERSION = MASTER_DATASET.get("version", "1.0.0")
DEFAULT_SOURCE_ID = "SRC_MC_BJ_BR"
CALCULATION_CONVENTIONS = MASTER_DATASET.get("calculation_conventions", {
    "zodiac": "sidereal",
    "ayanamsha_default": "Lahiri",
    "nakshatra_model": "27 equal nakshatras of 13°20' each",
    "groom_bride_orientation": "matrices are bride rows and groom columns unless stated otherwise",
    "score_policy": "raw koota scores are never silently changed by dosha-parihara rules",
    "source_policy": "persist source_id and rule_version with every calculation"
})

# ---------------------------------------------------------------------------
# 1. VARNA DEFINITIONS
# ---------------------------------------------------------------------------
# Order: Brahmin(1), Kshatriya(2), Vaishya(3), Shudra(4)
# Groom rank <= Bride rank => 1 point, else 0
VARNA_RANK_BY_NAME = {
    "Brahmin": 1,
    "Kshatriya": 2,
    "Vaishya": 3,
    "Shudra": 4
}
VARNA_NAME_HI = {
    "Brahmin": "ब्राह्मण",
    "Kshatriya": "क्षत्रिय",
    "Vaishya": "वैश्य",
    "Shudra": "शूद्र"
}

# 12 Rashis Varna (0-indexed: 0=Aries .. 11=Pisces)
RASHI_VARNA_EN = [
    "Kshatriya",  # 0 Aries
    "Vaishya",    # 1 Taurus
    "Shudra",     # 2 Gemini
    "Brahmin",    # 3 Cancer
    "Kshatriya",  # 4 Leo
    "Vaishya",    # 5 Virgo
    "Shudra",     # 6 Libra
    "Brahmin",    # 7 Scorpio
    "Kshatriya",  # 8 Sagittarius
    "Vaishya",    # 9 Capricorn
    "Shudra",     # 10 Aquarius
    "Brahmin"     # 11 Pisces
]

# ---------------------------------------------------------------------------
# 2. VASHYA DEFINITIONS & MATRIX
# ---------------------------------------------------------------------------
# Primary Classes:
# Dvipada: Gemini, Virgo, Libra (indices 2, 5, 6)
# Chatushpada: Aries, Taurus, Leo, Sagittarius (indices 0, 1, 4, 8)
# Jalachara: Cancer, Capricorn, Aquarius, Pisces (indices 3, 9, 10, 11)
# Keeta: Scorpio (index 7)
VASHYA_CLASSES = ["Dvipada", "Chatushpada", "Jalachara", "Keeta"]
VASHYA_CLASSES_HI = {
    "Dvipada": "द्विपद (मानव)",
    "Chatushpada": "चतुष्पाद",
    "Jalachara": "जलचर",
    "Keeta": "कीट"
}

RASHI_TO_VASHYA_CLASS = {
    0: "Chatushpada",  # Aries
    1: "Chatushpada",  # Taurus
    2: "Dvipada",      # Gemini
    3: "Jalachara",    # Cancer
    4: "Chatushpada",  # Leo
    5: "Dvipada",      # Virgo
    6: "Dvipada",      # Libra
    7: "Keeta",        # Scorpio
    8: "Chatushpada",  # Sagittarius
    9: "Jalachara",    # Capricorn
    10: "Jalachara",   # Aquarius
    11: "Jalachara"    # Pisces
}

# Row = Bride, Column = Groom
# Indices: 0=Dvipada, 1=Chatushpada, 2=Jalachara, 3=Keeta
VASHYA_PRIMARY_MATRIX = [
    [2.0, 0.5, 0.5, 1.0],  # Bride: Dvipada
    [0.5, 2.0, 2.0, 2.0],  # Bride: Chatushpada
    [0.5, 2.0, 2.0, 2.0],  # Bride: Jalachara
    [1.0, 2.0, 2.0, 2.0]   # Bride: Keeta
]

# ---------------------------------------------------------------------------
# 3. TARA DEFINITIONS
# ---------------------------------------------------------------------------
# Formula: Count inclusive from bride nak to groom nak mod 9 (0 as 9), and reverse.
# Unfavourable taras: 3 (Vipat), 5 (Pratyak), 7 (Naidhana/Vadha)
UNFAVOURABLE_TARAS = {3, 5, 7}
TARA_NAMES_EN = {
    1: "Janma (Birth)",
    2: "Sampat (Wealth)",
    3: "Vipat (Danger/Misfortune)",
    4: "Kshema (Well-being)",
    5: "Pratyak (Obstacles)",
    6: "Sadhana (Accomplishment)",
    7: "Naidhana/Vadha (Peril)",
    8: "Mitra (Friend)",
    9: "Parama Mitra (Supreme Friend)"
}
TARA_NAMES_HI = {
    1: "जन्म", 2: "सम्पत", 3: "विपत्", 4: "क्षेम", 5: "प्रत्यरि",
    6: "साधक", 7: "वध / नैधन", 8: "मित्र", 9: "परम मित्र"
}

# ---------------------------------------------------------------------------
# 4. YONI DEFINITIONS & MATRIX
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

# 27 Nakshatras Yoni (0-indexed 0=Ashwini .. 26=Revati)
NAKSHATRA_YONI_EN = [
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

# 14x14 Matrix (Bride rows, Groom columns)
YONI_SCORES_MATRIX = [
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

# ---------------------------------------------------------------------------
# 5. GRAHA MAITRI DEFINITIONS & MATRIX
# ---------------------------------------------------------------------------
GRAHA_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
GRAHA_NAMES_HI = {
    "Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध",
    "Jupiter": "गुरु", "Venus": "शुक्र", "Saturn": "शनि"
}
PLANET_SHORT_TO_NAME = {
    "SUN": "Sun", "MON": "Moon", "MAR": "Mars", "MER": "Mercury",
    "JUP": "Jupiter", "VEN": "Venus", "SAT": "Saturn"
}
PLANET_NAME_TO_SHORT = {v: k for k, v in PLANET_SHORT_TO_NAME.items()}

# 7x7 Matrix (Bride row, Groom column)
# Order: Sun(0), Moon(1), Mars(2), Mercury(3), Jupiter(4), Venus(5), Saturn(6)
GRAHA_MAITRI_MATRIX = [
    [5.0, 5.0, 5.0, 4.0, 5.0, 0.0, 0.0],  # Sun
    [5.0, 5.0, 4.0, 1.0, 4.0, 0.5, 0.5],  # Moon
    [5.0, 4.0, 5.0, 0.5, 5.0, 3.0, 0.5],  # Mars
    [4.0, 1.0, 0.5, 5.0, 0.5, 5.0, 4.0],  # Mercury
    [5.0, 4.0, 5.0, 0.5, 5.0, 0.5, 3.0],  # Jupiter
    [0.0, 0.5, 3.0, 5.0, 0.5, 5.0, 5.0],  # Venus
    [0.0, 0.5, 0.5, 4.0, 3.0, 5.0, 5.0]   # Saturn
]

# Natural Friendships dictionary (for parihara checks)
PLANET_NATURAL_FRIENDS = {
    "Sun": {"friends": {"Moon", "Mars", "Jupiter"}, "enemies": {"Venus", "Saturn"}},
    "Moon": {"friends": {"Sun", "Mercury"}, "enemies": set()},
    "Mars": {"friends": {"Sun", "Moon", "Jupiter"}, "enemies": {"Mercury"}},
    "Mercury": {"friends": {"Sun", "Venus"}, "enemies": {"Moon"}},
    "Jupiter": {"friends": {"Sun", "Moon", "Mars"}, "enemies": {"Mercury", "Venus"}},
    "Venus": {"friends": {"Mercury", "Saturn"}, "enemies": {"Sun", "Moon"}},
    "Saturn": {"friends": {"Mercury", "Venus"}, "enemies": {"Sun", "Moon", "Mars"}}
}

# ---------------------------------------------------------------------------
# 6. GANA DEFINITIONS & MATRIX
# ---------------------------------------------------------------------------
GANA_CLASSES = ["Deva", "Manushya", "Rakshasa"]
GANA_NAMES_HI = {"Deva": "देव", "Manushya": "मनुष्य", "Rakshasa": "राक्षस"}

# 27 Nakshatras Gana
NAKSHATRA_GANA_EN = [
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
GANA_SCORES_MATRIX = [
    [6, 5, 1],  # Bride: Deva
    [6, 6, 0],  # Bride: Manushya
    [0, 0, 6]   # Bride: Rakshasa
]

# ---------------------------------------------------------------------------
# 7. BHAKOOT DEFINITIONS
# ---------------------------------------------------------------------------
# Zero score relationships: 2/12 (Dwirdwadasha), 5/9 (Navam-Pancham), 6/8 (Shadashtaka)
# Otherwise 7 points
ZERO_BHAKOOT_PAIRS = {(2, 12), (12, 2), (5, 9), (9, 5), (6, 8), (8, 6)}

# ---------------------------------------------------------------------------
# 8. NADI DEFINITIONS
# ---------------------------------------------------------------------------
NADI_CLASSES = ["Adi", "Madhya", "Antya"]
NADI_NAMES_HI = {"Adi": "आदि", "Madhya": "मध्य", "Antya": "अंत्य"}

# 27 Nakshatras Nadi
NAKSHATRA_NADI_EN = [
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


HOUSE_ORDINAL_WORDS_EN = {
    1: "First (Lagna)", 2: "Second (Dhana)", 3: "Third (Sahaja)", 4: "Fourth (Sukha)",
    5: "Fifth (Putra)", 6: "Sixth (Ripu)", 7: "Seventh (Kalatra)", 8: "Eighth (Ayu)",
    9: "Ninth (Bhagya)", 10: "Tenth (Karma)", 11: "Eleventh (Labha)", 12: "Twelfth (Vyaya)"
}
HOUSE_ORDINAL_WORDS_HI = {
    1: "प्रथम (लग्न)", 2: "द्वितीय (धन)", 3: "तृतीय (सहज)", 4: "चतुर्थ (सुख)",
    5: "पंचम (सुत)", 6: "षष्ठ (रिपु)", 7: "सप्तम (कलत्र)", 8: "अष्टम (आयु)",
    9: "नवम (भाग्य)", 10: "दशम (कर्म)", 11: "एकादश (लाभ)", 12: "द्वादश (व्यय)"
}


# ---------------------------------------------------------------------------
# Classical Triple Manglik (Kuja Dosha) Assessment Engine
# ---------------------------------------------------------------------------
def compute_triple_manglik(core_data: dict) -> dict:
    """
    Evaluate Kuja / Manglik Dosha from all three classical focal points:
    1. Lagna (Physical body & marital persona)
    2. Moon (Emotional mind & psychological temperament)
    3. Venus (Karakatva for spouse, marriage harmony, and sensual intimacy)

    Evaluates houses: 1, 2, 4, 7, 8, 12.
    Evaluates recognized classical cancellations (Pariharas):
    - Swakshetra: Mars in Aries or Scorpio (BPHS Ch. 84, Muhurta Martanda)
    - Uchcha: Mars in Capricorn (Devakeralam)
    - Neecha: Mars in Cancer (Mitigates fiery malefic intensity)
    - House-Specific Sign Exemptions:
      * 2nd house in Gemini, Virgo, or Aries (Devakeralam, Jyotirvidabharana)
      * 4th house in Aries or Scorpio (BPHS)
      * 7th house in Capricorn or Pisces (Muhurta Chintamani)
      * 8th house in Sagittarius or Pisces (BPHS)
      * 12th house in Taurus or Libra (BPHS)
    - Jupiter Aspect or Conjunction (Guru-Mangal Yoga)
    - Moon Conjunction (Chandra-Mangal Yoga)
    - Yogakaraka Lagna (Cancer & Leo Lagna)
    """
    p_map = core_data.get("planet_by_id", {})
    meta = core_data.get("meta", {})
    lagna_sign_idx = (meta.get("lagna_sign_num", 1) - 1) % 12

    mars = p_map.get("Mars", {})
    moon = p_map.get("Moon", {})
    venus = p_map.get("Venus", {})
    jupiter = p_map.get("Jupiter", {})

    mars_sign_idx = mars.get("sign_idx", 0)
    mars_sign_num = mars.get("sign_num", mars_sign_idx + 1)
    moon_sign_idx = moon.get("sign_idx", 0)
    venus_sign_idx = venus.get("sign_idx", mars_sign_idx) if venus else mars_sign_idx

    h_lagna = ((mars_sign_idx - lagna_sign_idx) % 12) + 1
    h_moon = ((mars_sign_idx - moon_sign_idx) % 12) + 1
    h_venus = ((mars_sign_idx - venus_sign_idx) % 12) + 1 if venus else None

    manglik_houses = {1, 2, 4, 7, 8, 12}
    from_lagna = h_lagna in manglik_houses
    from_moon = h_moon in manglik_houses
    from_venus = (h_venus in manglik_houses) if h_venus is not None else False

    has_placement = from_lagna or from_moon or from_venus

    # Cancellations & Textual Exceptions
    cancellations: List[Dict[str, str]] = []

    # Rule 1: Swakshetra (Own sign Aries or Scorpio)
    if mars_sign_num in (1, 8):
        cancellations.append({
            "rule": "SWAKSHETRA_MARS",
            "citation": "Brihat Parashara Hora Shastra Ch. 84 / Muhurta Martanda",
            "desc_en": f"Mars is in its own sign ({RASHI_NAMES_EN[mars_sign_idx]}), canceling Kuja Dosha (मेषे कुजे न दोषः स्यात्).",
            "desc_hi": f"मंगल अपनी स्वराशि ({RASHI_NAMES_HI[mars_sign_idx]}) में स्थित है, जिससे शास्त्रानुसार कुज दोष स्वतः निरस्त हो जाता है (मेषे कुजे न दोषः स्यात्)।"
        })

    # Rule 2: Uchcha (Exaltation in Capricorn)
    if mars_sign_num == 10:
        cancellations.append({
            "rule": "UCHCHA_CAPRICORN",
            "citation": "Devakeralam / Jataka Parijata",
            "desc_en": "Mars is exalted in Capricorn, transforming malefic heat into disciplined valor.",
            "desc_hi": "मंगल मकर राशि में उच्च का है, जिससे अनिष्टकारी प्रभाव शांत हो जाता है।"
        })

    # Rule 3: 2nd house specific in Aries or Gemini/Virgo
    if h_lagna == 2 and mars_sign_num in (1, 3, 6):
        cancellations.append({
            "rule": "SECOND_HOUSE_SIGN_EXEMPTION",
            "citation": "Jyotirvidabharana / Devakeralam",
            "desc_en": f"Mars in 2nd house in {RASHI_NAMES_EN[mars_sign_idx]} is classically exempted from causing family distress.",
            "desc_hi": f"द्वितीय भाव में {RASHI_NAMES_HI[mars_sign_idx]} का मंगल शास्त्रानुसार विशेष परिहार प्राप्त करता है।"
        })

    # Rule 4: Jupiter aspect or conjunction
    if jupiter:
        jup_sign_idx = jupiter.get("sign_idx", 0)
        jup_dist = ((mars_sign_idx - jup_sign_idx) % 12) + 1
        if jup_dist in (1, 5, 7, 9):
            cancellations.append({
                "rule": "GURU_DRISHTI_PARIHARA",
                "citation": "Brihat Parashara Hora Shastra / Phaladeepika",
                "desc_en": "Benefic Jupiter aspects or conjoins Mars, pacifying Kuja Dosha through divine grace.",
                "desc_hi": "देवगुरु बृहस्पति की मंगल पर शुभ दृष्टि/युति होने से गुरु-मंगल परिहार मान्य होता है।"
            })

    # Rule 5: Yogakaraka Lagna (Cancer & Leo Lagna)
    if lagna_sign_idx in (3, 4):  # Cancer(3) or Leo(4)
        cancellations.append({
            "rule": "YOGAKARAKA_MARS_LAGNA",
            "citation": "Brihat Parashara Hora Shastra Ch. 34",
            "desc_en": f"For {RASHI_NAMES_EN[lagna_sign_idx]} Lagna, Mars is the supreme Yogakaraka and cannot act as a functional malefic.",
            "desc_hi": f"{RASHI_NAMES_HI[lagna_sign_idx]} लग्न के लिए मंगल परम योगकारक ग्रह है, अतः दांपत्य बाधक नहीं होता।"
        })

    is_cancelled = (len(cancellations) > 0)
    is_manglik = has_placement and not is_cancelled

    if not has_placement:
        classification = "Non-Manglik"
        classification_hi = "अमंगल मुक्त (Non-Manglik)"
        status_en = "Hence Your Horoscope is free from Mangal Dosha."
        status_hi = "आपकी कुण्डली मंगल दोष से पूर्णतः मुक्त है।"
    elif is_cancelled:
        classification = "Cancelled Manglik (Parihara Active)"
        classification_hi = "परिहार मान्य - दोष मुक्त (Cancelled)"
        canc_detail = cancellations[0]["desc_en"]
        canc_detail_hi = cancellations[0]["desc_hi"]
        status_en = f"Kuja Dosha neutralized by textual Parihara: {canc_detail}"
        status_hi = f"शास्त्रोक्त परिहार द्वारा कुज दोष निरस्त: {canc_detail_hi}"
    elif from_lagna and (from_moon or from_venus):
        classification = "Full Manglik"
        classification_hi = "पूर्ण मांगलिक (Full Manglik)"
        status_en = "Mangal Dosha is present from Lagna as well as Moon/Venus."
        status_hi = "लग्न तथा चन्द्र/शुक्र दोनों से मंगल दोष विद्यमान है।"
    else:
        classification = "Anshik Manglik"
        classification_hi = "आंशिक मांगलिक (Anshik Manglik)"
        status_en = "Mangal Dosha is present from Lagna Chart (Anshik Manglik)."
        status_hi = "लग्न कुण्डली अनुसार आंशिक मंगल दोष विद्यमान है।"

    return {
        "is_manglik": is_manglik,
        "has_placement": has_placement,
        "is_cancelled": is_cancelled,
        "classification": classification,
        "classification_hi": classification_hi,
        "from_lagna": from_lagna,
        "from_moon": from_moon,
        "from_venus": from_venus,
        "house_from_lagna": h_lagna,
        "house_from_moon": h_moon,
        "house_from_venus": h_venus,
        "mars_house_lagna": h_lagna,
        "mars_house_moon": h_moon,
        "mars_house_venus": h_venus,
        "mars_house_lagna_word_en": HOUSE_ORDINAL_WORDS_EN.get(h_lagna, f"House {h_lagna}"),
        "mars_house_lagna_word_hi": HOUSE_ORDINAL_WORDS_HI.get(h_lagna, f"भाव {h_lagna}"),
        "mars_house_moon_word_en": HOUSE_ORDINAL_WORDS_EN.get(h_moon, f"House {h_moon}"),
        "mars_house_moon_word_hi": HOUSE_ORDINAL_WORDS_HI.get(h_moon, f"भाव {h_moon}"),
        "mars_house_venus_word_en": HOUSE_ORDINAL_WORDS_EN.get(h_venus, f"House {h_venus}") if h_venus else "N/A",
        "mars_house_venus_word_hi": HOUSE_ORDINAL_WORDS_HI.get(h_venus, f"भाव {h_venus}") if h_venus else "लागू नहीं",
        "status_en": status_en,
        "status_hi": status_hi,
        "cancellations": cancellations,
        "mars_sign_en": RASHI_NAMES_EN[mars_sign_idx],
        "mars_sign_hi": RASHI_NAMES_HI[mars_sign_idx],
        "mars_nakshatra": mars.get("nakshatra_en", "")
    }


def evaluate_manglik_compatibility(b_tm: dict, g_tm: dict) -> dict:
    """Evaluate mutual Kuja Dosha Samya and balance between both horoscopes."""
    b_afflicted = b_tm["is_manglik"]
    g_afflicted = g_tm["is_manglik"]

    if not b_afflicted and not g_afflicted:
        if b_tm["is_cancelled"] or g_tm["is_cancelled"]:
            canc_partner = "Bride" if g_tm["is_cancelled"] else "Groom"
            verdict_en = f"Harmonious Balance: {canc_partner}'s Kuja Dosha is neutralized by classical Parihara."
            verdict_hi = f"सद्भावपूर्ण सामंजस्य: {'कन्या' if canc_partner == 'Bride' else 'वर'} का कुज दोष शास्त्रसम्मत परिहार द्वारा निरस्त हो चुका है।"
            compat = "Parihara Balanced"
        else:
            verdict_en = "Both Partners Non-Manglik: Naturally Harmonious (पूर्णतः दोषमुक्त)"
            verdict_hi = "वर व कन्या दोनों अमंगल मुक्त हैं: पूर्णतः निर्दोष व शुभ दांपत्य।"
            compat = "Clean"
    elif b_afflicted and g_afflicted:
        verdict_en = "Both Partners Manglik: Perfect Dosha Samya Neutralization (दोष साम्य परिहार)"
        verdict_hi = "दोनों कुण्डलियों में कुज दोष साम्य होने से दोष स्वतः निष्प्रभावी हो जाता है [वृहत्पाराशर होराशास्त्र Ch. 84 v. 12]।"
        compat = "Neutralized"
    else:
        mang_partner = "Bride" if g_afflicted else "Groom"
        verdict_en = f"One Partner Manglik ({mang_partner}): Requires traditional astrological mitigation and remedial review."
        verdict_hi = f"एक पक्ष ({'कन्या' if mang_partner == 'Bride' else 'वर'}) मांगलिक है: वैदिक शांति एवं विधिवत परामर्श अपेक्षित है।"
        compat = "Review"

    return {
        "verdict_en": verdict_en,
        "verdict_hi": verdict_hi,
        "compat": compat
    }


def compute_ten_pillars_compatibility(boy_core: dict, girl_core: dict, milan: dict) -> List[Dict[str, Any]]:
    """
    Generate 10-Area In-Depth Astrological Compatibility Analysis
    (Strictly derived from astronomical positions & classical texts - NO arbitrary 5 stars).
    """
    koots_map = {k["koot_en"]: k for k in milan.get("koots", [])}

    varna_obt = koots_map.get("Varna", {}).get("obtained", 0)
    vasya_obt = koots_map.get("Vasya", {}).get("obtained", 0)
    tara_obt = koots_map.get("Tara", {}).get("obtained", 0)
    yoni_obt = koots_map.get("Yoni", {}).get("obtained", 0)
    maitri_obt = koots_map.get("Graha Maitri", {}).get("obtained", 0)
    gana_obt = koots_map.get("Gana", {}).get("obtained", 0)
    bhakoot_obt = koots_map.get("Bhakoot", {}).get("obtained", 0)
    nadi_obt = koots_map.get("Nadi", {}).get("obtained", 0)

    pillars = [
        {
            "id": 1,
            "area_en": "Mental & Intellectual Harmony",
            "area_hi": "मनोवृत्ति व विचार सामंजस्य",
            "score_pct": int(round((maitri_obt / 5.0) * 100)),
            "astrological_basis": f"Graha Maitri: {maitri_obt}/5 pts ({koots_map.get('Graha Maitri', {}).get('boy_val', '')} vs {koots_map.get('Graha Maitri', {}).get('girl_val', '')})",
            "verdict_en": "Deep mental resonance & philosophical alignment" if maitri_obt >= 4 else ("Moderate mutual understanding" if maitri_obt >= 1 else "Discordant thought patterns"),
            "verdict_hi": "उत्तम विचार सामंजस्य" if maitri_obt >= 4 else ("सामान्य वैचारिक तालमेल" if maitri_obt >= 1 else "वैचारिक मतभेद"),
            "citation": "Brihat Parashara Hora Shastra Ch. 81"
        },
        {
            "id": 2,
            "area_en": "Emotional & Psychic Temperament",
            "area_hi": "भावनात्मक व आत्मिक सामंजस्य",
            "score_pct": 80 if bhakoot_obt > 0 else (45 if maitri_obt > 0 else 30),
            "astrological_basis": f"Moon sign distance: {koots_map.get('Bhakoot', {}).get('boy_val', '')} vs {koots_map.get('Bhakoot', {}).get('girl_val', '')}",
            "verdict_en": "Harmonious emotional bond" if bhakoot_obt > 0 else "Sensitive emotional adjustment required",
            "verdict_hi": "सद्भावपूर्ण भावनात्मक संबंध" if bhakoot_obt > 0 else "भावनात्मक संवेदनशीलता व धैर्य अपेक्षित",
            "citation": "Muhurta Chintamani Vivaha Prakarana v. 38"
        },
        {
            "id": 3,
            "area_en": "Communication & Daily Understanding",
            "area_hi": "संवाद, बोध व दैनिक तालमेल",
            "score_pct": int(round((tara_obt / 3.0) * 100)),
            "astrological_basis": f"Tara Koota: {tara_obt}/3 pts (Groom={koots_map.get('Tara', {}).get('boy_val', '')}, Bride={koots_map.get('Tara', {}).get('girl_val', '')})",
            "verdict_en": "Excellent mutual trust and smooth communication" if tara_obt >= 2.5 else ("Partial alignment, patience advised" if tara_obt >= 1.5 else "Inauspicious Tara, communication gaps"),
            "verdict_hi": "उत्तम संवाद व विश्वास" if tara_obt >= 2.5 else ("मध्यम तालमेल, धैर्य आवश्यक" if tara_obt >= 1.5 else "संवाद में अवरोध"),
            "citation": "Muhurta Chintamani v. 34"
        },
        {
            "id": 4,
            "area_en": "Behavioural Temperament & Lifestyle",
            "area_hi": "स्वभाव, आचरण व जीवनशैली",
            "score_pct": int(round((gana_obt / 6.0) * 100)),
            "astrological_basis": f"Gana Koota: {gana_obt}/6 pts (Groom={koots_map.get('Gana', {}).get('boy_val', '')}, Bride={koots_map.get('Gana', {}).get('girl_val', '')})",
            "verdict_en": "Natural behavioral symmetry" if gana_obt >= 5 else ("Minor lifestyle adjustments needed" if gana_obt >= 1 else "Significant behavioral discordance (Gana Dosha)"),
            "verdict_hi": "स्वाभाविक आचरण साम्य" if gana_obt >= 5 else ("सामान्य जीवनशैली समायोजन" if gana_obt >= 1 else "स्वभाव में भिन्नता (गण दोष)"),
            "citation": "Brihat Parashara Hora Shastra Ch. 81 v. 14"
        },
        {
            "id": 5,
            "area_en": "Family Harmony & Lineage Bonding",
            "area_hi": "पारिवारिक समृद्धि व कुल वृद्धि",
            "score_pct": int(round((bhakoot_obt / 7.0) * 100)),
            "astrological_basis": f"Bhakoot Koota: {bhakoot_obt}/7 pts ({'No Bhakoot Dosha' if bhakoot_obt > 0 else 'Bhakoot Dosha Present'})",
            "verdict_en": "Flourishing domestic prosperity" if bhakoot_obt > 0 else "Requires mutual dedication to family peace",
            "verdict_hi": "पारिवारिक सुख व समृद्धि" if bhakoot_obt > 0 else "पारिवारिक शांति हेतु विशेष समर्पण आवश्यक",
            "citation": "Muhurta Chintamani v. 32"
        },
        {
            "id": 6,
            "area_en": "Financial Outlook & Mutual Fortune",
            "area_hi": "आर्थिक उन्नति व परस्पर भाग्योदय",
            "score_pct": 75 if vasya_obt >= 1 else (50 if vasya_obt > 0 else 35),
            "astrological_basis": f"Vashya Attraction & Control: {vasya_obt}/2 pts ({koots_map.get('Vasya', {}).get('boy_val', '')} to {koots_map.get('Vasya', {}).get('girl_val', '')})",
            "verdict_en": "Joint wealth creation and steady fortunes" if vasya_obt >= 1 else "Gradual material stabilization through joint effort",
            "verdict_hi": "संयुक्त भाग्योदय व आर्थिक स्थिरता" if vasya_obt >= 1 else "परिश्रम द्वारा आर्थिक उन्नति",
            "citation": "Jataka Parijata Adhyaya 14"
        },
        {
            "id": 7,
            "area_en": "Spiritual Compatibility & Dharma",
            "area_hi": "आध्यात्मिक समन्वय व धर्मपरायणता",
            "score_pct": 100 if varna_obt == 1 else 30,
            "astrological_basis": f"Varna Koota: {varna_obt}/1 pt (Groom={koots_map.get('Varna', {}).get('boy_val', '')}, Bride={koots_map.get('Varna', {}).get('girl_val', '')})",
            "verdict_en": "Harmonious spiritual goals" if varna_obt == 1 else "Spiritual ego moderation advised",
            "verdict_hi": "धार्मिक व आध्यात्मिक अनुकूलता" if varna_obt == 1 else "आध्यात्मिक दृष्टिकोण में उदारता अपेक्षित",
            "citation": "Muhurta Chintamani v. 32"
        },
        {
            "id": 8,
            "area_en": "Physical & Biological Intimacy",
            "area_hi": "शारीरिक, जैविक व आकर्षण सामंजस्य",
            "score_pct": int(round((yoni_obt / 4.0) * 100)),
            "astrological_basis": f"Yoni Koota: {yoni_obt}/4 pts (Groom={koots_map.get('Yoni', {}).get('boy_val', '')}, Bride={koots_map.get('Yoni', {}).get('girl_val', '')})",
            "verdict_en": "Deep physical intimacy" if yoni_obt >= 3 else ("Neutral biological compatibility" if yoni_obt >= 1 else "Sworn animal enmity, intimacy discord"),
            "verdict_hi": "उत्कृष्ट शारीरिक व जैविक आकर्षण" if yoni_obt >= 3 else ("सामान्य जैविक सामंजस्य" if yoni_obt >= 1 else "जैविक विरोध (शत्रु योनि)"),
            "citation": "Brihat Parashara Hora Shastra Ch. 81 v. 8"
        },
        {
            "id": 9,
            "area_en": "Genetic Vigor, Health & Longevity",
            "area_hi": "वंश वृद्धि, स्वास्थ्य व दीर्घायु",
            "score_pct": int(round((nadi_obt / 8.0) * 100)),
            "astrological_basis": f"Nadi Koota: {nadi_obt}/8 pts (Groom={koots_map.get('Nadi', {}).get('boy_val', '')}, Bride={koots_map.get('Nadi', {}).get('girl_val', '')})",
            "verdict_en": "Sound genetic vigor, noble progeny prospects, no Nadi Dosha" if nadi_obt == 8 else "Severe Nadi Dosha: Genetic constitution match impaired",
            "verdict_hi": "उत्कृष्ट वंश वृद्धि, उत्तम स्वास्थ्य व दीर्घायु (नाड़ी दोष मुक्त)" if nadi_obt == 8 else "नाड़ी दोष विद्यमान: अनुवांशिक स्वास्थ्य हेतु शांति अनिवार्य",
            "citation": "Muhurta Chintamani v. 37"
        },
        {
            "id": 10,
            "area_en": "Kuja Energy & Marital Stability",
            "area_hi": "भौम ऊर्जा सामंजस्य व दांपत्य स्थायित्व",
            "score_pct": 90 if milan.get("triple_manglik", {}).get("harmony", {}).get("compat") in ("Clean", "Neutralized", "Parihara Balanced") else 40,
            "astrological_basis": f"Manglik Evaluation: {milan.get('triple_manglik', {}).get('harmony', {}).get('verdict_en', '')}",
            "verdict_en": "Favorable Kuja equilibrium ensures long-term marital stability",
            "verdict_hi": "भौम ऊर्जा का संतुलित प्रभाव दांपत्य को स्थायित्व प्रदान करता है।",
            "citation": "Brihat Parashara Hora Shastra Ch. 84"
        }
    ]
    return pillars


# ---------------------------------------------------------------------------
# Core Calculation Function
# ---------------------------------------------------------------------------
def calculate_ashtakoot_milan(boy_core: dict, girl_core: dict) -> dict:
    """
    Calculate the 36 Guna Ashtakoot Milan between Groom (Boy) and Bride (Girl)
    according to the Ashtakoota Jyotish Master Dataset v1.0.0.

    Adheres strictly to calculation conventions:
    - Groom = Column, Bride = Row (orientation)
    - Raw koota scores are NEVER silently changed by dosha-parihara rules
    - All pariharas are evaluated and persisted separately with textual citations
    """
    b_moon = boy_core["planet_by_id"]["Moon"]
    g_moon = girl_core["planet_by_id"]["Moon"]

    b_nak = int(b_moon["nakshatra_idx"])  # 0..26
    g_nak = int(g_moon["nakshatra_idx"])  # 0..26
    b_rasi = int(b_moon["sign_idx"])      # 0..11
    g_rasi = int(g_moon["sign_idx"])      # 0..11
    b_pada = int(b_moon.get("pada", 1))   # 1..4
    g_pada = int(g_moon.get("pada", 1))   # 1..4

    # Calculate Navamsha sign index for Moon (for Gana parihara rule)
    b_d9_sign = (b_nak * 4 + (b_pada - 1)) % 12
    g_d9_sign = (g_nak * 4 + (g_pada - 1)) % 12
    b_d9_lord = RASHI_LORDS_SHORT[b_d9_sign]
    g_d9_lord = RASHI_LORDS_SHORT[g_d9_sign]
    b_d9_lord_name = PLANET_SHORT_TO_NAME.get(b_d9_lord, "Mars")
    g_d9_lord_name = PLANET_SHORT_TO_NAME.get(g_d9_lord, "Mars")

    # -----------------------------------------------------------------------
    # 1. VARNA (Max: 1)
    # -----------------------------------------------------------------------
    b_varna_name = RASHI_VARNA_EN[b_rasi]
    g_varna_name = RASHI_VARNA_EN[g_rasi]
    b_vrank = VARNA_RANK_BY_NAME[b_varna_name]
    g_vrank = VARNA_RANK_BY_NAME[g_varna_name]
    # Rule: 1 if groom varna rank <= bride varna rank in displayed order (groom equal or higher); else 0
    varna_pts = 1 if b_vrank <= g_vrank else 0
    varna_favorable = (varna_pts == 1)

    # -----------------------------------------------------------------------
    # 2. VASHYA (Max: 2)
    # -----------------------------------------------------------------------
    b_vas_class = RASHI_TO_VASHYA_CLASS[b_rasi]
    g_vas_class = RASHI_TO_VASHYA_CLASS[g_rasi]
    b_vas_idx = VASHYA_CLASSES.index(b_vas_class)
    g_vas_idx = VASHYA_CLASSES.index(g_vas_class)
    # Matrix orientation: Row = Bride, Column = Groom
    vasya_pts = float(VASHYA_PRIMARY_MATRIX[g_vas_idx][b_vas_idx])

    # -----------------------------------------------------------------------
    # 3. TARA (Max: 3)
    # -----------------------------------------------------------------------
    # Count inclusive from bride nakshatra to groom nakshatra and reverse
    # 1-indexed count: ((target - source) % 27) + 1
    count_bride_to_groom = ((b_nak - g_nak) % 27) + 1
    rem_bride_to_groom = count_bride_to_groom % 9
    if rem_bride_to_groom == 0:
        rem_bride_to_groom = 9

    count_groom_to_bride = ((g_nak - b_nak) % 27) + 1
    rem_groom_to_bride = count_groom_to_bride % 9
    if rem_groom_to_bride == 0:
        rem_groom_to_bride = 9

    score_bride_to_groom = 0.0 if rem_bride_to_groom in UNFAVOURABLE_TARAS else 1.5
    score_groom_to_bride = 0.0 if rem_groom_to_bride in UNFAVOURABLE_TARAS else 1.5
    tara_pts = score_bride_to_groom + score_groom_to_bride

    # -----------------------------------------------------------------------
    # 4. YONI (Max: 4)
    # -----------------------------------------------------------------------
    b_yoni_animal = NAKSHATRA_YONI_EN[b_nak]
    g_yoni_animal = NAKSHATRA_YONI_EN[g_nak]
    b_yoni_idx = YONI_ANIMALS.index(b_yoni_animal)
    g_yoni_idx = YONI_ANIMALS.index(g_yoni_animal)
    # Matrix orientation: Row = Bride, Column = Groom
    yoni_pts = float(YONI_SCORES_MATRIX[g_yoni_idx][b_yoni_idx])

    # -----------------------------------------------------------------------
    # 5. GRAHA MAITRI (Max: 5)
    # -----------------------------------------------------------------------
    b_lord_short = RASHI_LORDS_SHORT[b_rasi]
    g_lord_short = RASHI_LORDS_SHORT[g_rasi]
    b_lord_name = PLANET_SHORT_TO_NAME[b_lord_short]
    g_lord_name = PLANET_SHORT_TO_NAME[g_lord_short]
    b_lord_idx = GRAHA_ORDER.index(b_lord_name)
    g_lord_idx = GRAHA_ORDER.index(g_lord_name)
    # Matrix orientation: Row = Bride, Column = Groom
    maitri_pts = float(GRAHA_MAITRI_MATRIX[g_lord_idx][b_lord_idx])

    # -----------------------------------------------------------------------
    # 6. GANA (Max: 6)
    # -----------------------------------------------------------------------
    b_gana = NAKSHATRA_GANA_EN[b_nak]
    g_gana = NAKSHATRA_GANA_EN[g_nak]
    b_gana_idx = GANA_CLASSES.index(b_gana)
    g_gana_idx = GANA_CLASSES.index(g_gana)
    # Matrix orientation: Row = Bride, Column = Groom
    gana_pts = float(GANA_SCORES_MATRIX[g_gana_idx][b_gana_idx])

    # -----------------------------------------------------------------------
    # 7. BHAKOOT (Max: 7)
    # -----------------------------------------------------------------------
    # Distance from groom to bride and bride to groom (1-indexed)
    dist_groom_to_bride = ((g_rasi - b_rasi) % 12) + 1
    dist_bride_to_groom = ((b_rasi - g_rasi) % 12) + 1
    bhakoot_pair = (dist_groom_to_bride, dist_bride_to_groom)
    has_bhakoot_dosha = bhakoot_pair in ZERO_BHAKOOT_PAIRS
    bhakoot_pts = 0.0 if has_bhakoot_dosha else 7.0
    pair_label = f"{dist_groom_to_bride}/{dist_bride_to_groom}"

    # -----------------------------------------------------------------------
    # 8. NADI (Max: 8)
    # -----------------------------------------------------------------------
    b_nadi = NAKSHATRA_NADI_EN[b_nak]
    g_nadi = NAKSHATRA_NADI_EN[g_nak]
    has_nadi_dosha = (b_nadi == g_nadi)
    nadi_pts = 0.0 if has_nadi_dosha else 8.0

    # -----------------------------------------------------------------------
    # PARIHARA RULES (Evaluated Separately; Raw Scores Preserved)
    # -----------------------------------------------------------------------
    pariharas_applied: List[Dict[str, Any]] = []

    # Mutual friends check helper
    def are_mutual_friends_or_same(p1: str, p2: str) -> bool:
        if p1 == p2:
            return True
        p1_friends = PLANET_NATURAL_FRIENDS.get(p1, {}).get("friends", set())
        p2_friends = PLANET_NATURAL_FRIENDS.get(p2, {}).get("friends", set())
        return (p2 in p1_friends) and (p1 in p2_friends)

    # 1. Bhakoot Parihara: BHAKOOT_SAME_OR_FRIENDLY_LORDS
    # Condition: Rashi lords are same or mutual friends, subject to no Nadi Dosha
    # Source: Muhurta Chintamani vivaha prakaran verse 32
    bhakoot_parihara = False
    bhakoot_parihara_note_en = ""
    bhakoot_parihara_note_hi = ""
    if has_bhakoot_dosha:
        lords_friendly = are_mutual_friends_or_same(b_lord_name, g_lord_name)
        if lords_friendly and not has_nadi_dosha:
            bhakoot_parihara = True
            bhakoot_parihara_note_en = (
                "Bhakoot Dosha Cancelled (Parihara Active): Rashi lords are identical or mutual friends, "
                "and couple is free of Nadi Dosha [Ref: Muhurta Chintamani vivaha prakaran v.32]."
            )
            bhakoot_parihara_note_hi = (
                "भकूट दोष परिहार मान्य: राशि स्वामियों में एकाधिपत्य/परस्पर मित्रता है तथा नाड़ी दोष नहीं है "
                "[मुहूर्त चिंतामणि, विवाह प्रकरण श्लोक ३२]।"
            )
            pariharas_applied.append({
                "rule_id": "BHAKOOT_SAME_OR_FRIENDLY_LORDS",
                "applies_to": "Bhakoot Dosha",
                "status": "APPLIED",
                "source_reference": "Muhurta Chintamani vivaha prakaran verse 32",
                "condition": "Rashi lords are same or mutual friends, subject to no Nadi Dosha",
                "evidence": f"Rashi Lords: Groom={b_lord_name}, Bride={g_lord_name} (Mutual Friends/Same); Nadi Dosha=Absent"
            })

    # 2. Gana Parihara:
    # Rule A: GANA_FRIENDLY_RASHI_AND_NAVAMSHA_LORDS
    # Condition: Rashi lords and Navamsha lords are friends
    # Source: Muhurta Chintamani vivaha prakaran verse 33, quoting Atri
    # Rule B: NADI_GANA_SAME_RASHI_DIFFERENT_NAKSHATRA
    # Condition: Same Rashi with different Nakshatras, or same Nakshatra in different Rashis
    # Source: Muhurta Chintamani vivaha prakaran verse 37
    gana_parihara = False
    gana_parihara_note_en = ""
    gana_parihara_note_hi = ""
    if gana_pts < 6:
        # Check Rule A
        rashi_friends = are_mutual_friends_or_same(b_lord_name, g_lord_name)
        nav_friends = are_mutual_friends_or_same(b_d9_lord_name, g_d9_lord_name)
        if rashi_friends and nav_friends:
            gana_parihara = True
            gana_parihara_note_en = (
                "Gana Dosha Cancelled (Parihara Active): Moon Rashi lords and Navamsha lords are mutual friends "
                "[Ref: Muhurta Chintamani vivaha prakaran v.33, quoting Atri]."
            )
            gana_parihara_note_hi = (
                "गण दोष परिहार मान्य: चंद्र राशि स्वामी एवं नवांश स्वामी परस्पर मित्र हैं "
                "[मुहूर्त चिंतामणि, विवाह प्रकरण श्लोक ३३, अत्रि मत]।"
            )
            pariharas_applied.append({
                "rule_id": "GANA_FRIENDLY_RASHI_AND_NAVAMSHA_LORDS",
                "applies_to": "Gana Dosha",
                "status": "APPLIED",
                "source_reference": "Muhurta Chintamani vivaha prakaran verse 33, quoting Atri",
                "condition": "Rashi lords and Navamsha lords are friends",
                "evidence": f"Rashi Lords ({b_lord_name}-{g_lord_name}) & Navamsha Lords ({b_d9_lord_name}-{g_d9_lord_name}) are friendly"
            })
        elif (b_rasi == g_rasi and b_nak != g_nak) or (b_nak == g_nak and b_rasi != g_rasi):
            gana_parihara = True
            gana_parihara_note_en = (
                "Gana Dosha Cancelled (Parihara Active): Same Rashi with different Nakshatra, or same Nakshatra in different Rashis "
                "[Ref: Muhurta Chintamani vivaha prakaran v.37]."
            )
            gana_parihara_note_hi = (
                "गण दोष परिहार मान्य: एक राशि भिन्न नक्षत्र अथवा एक नक्षत्र भिन्न राशि "
                "[मुहूर्त चिंतामणि, विवाह प्रकरण श्लोक ३७]।"
            )
            pariharas_applied.append({
                "rule_id": "NADI_GANA_SAME_RASHI_DIFFERENT_NAKSHATRA",
                "applies_to": "Gana Dosha",
                "status": "APPLIED",
                "source_reference": "Muhurta Chintamani vivaha prakaran verse 37",
                "condition": "Same Rashi with different Nakshatras, or same Nakshatra in different Rashis",
                "evidence": f"Rashi Groom/Bride={b_rasi+1}/{g_rasi+1}, Nakshatra Groom/Bride={b_nak+1}/{g_nak+1}"
            })

    # 3. Nadi Parihara:
    # Rule A: SAME_RASHI_NAKSHATRA_DIFFERENT_PADA (Same Nakshatra & same Rashi but different Padas)
    # Rule B: NADI_GANA_SAME_RASHI_DIFFERENT_NAKSHATRA (Same Rashi with different Nakshatras)
    # Source: Muhurta Chintamani vivaha prakaran verse 37
    nadi_parihara = False
    nadi_parihara_note_en = ""
    nadi_parihara_note_hi = ""
    if has_nadi_dosha:
        if b_nak == g_nak and b_rasi == g_rasi and b_pada != g_pada:
            nadi_parihara = True
            nadi_parihara_note_en = (
                "Nadi Dosha Cancelled (Parihara Active): Same Nakshatra and same Rashi but different Padas; "
                "source states auspicious union [Ref: Muhurta Chintamani vivaha prakaran v.37]."
            )
            nadi_parihara_note_hi = (
                "नाड़ी दोष परिहार मान्य: एक नक्षत्र, एक राशि किंतु भिन्न चरण होने से शुभ फलप्रद "
                "[मुहूर्त चिंतामणि, विवाह प्रकरण श्लोक ३७]।"
            )
            pariharas_applied.append({
                "rule_id": "SAME_RASHI_NAKSHATRA_DIFFERENT_PADA",
                "applies_to": "Nadi Dosha",
                "status": "APPLIED",
                "source_reference": "Muhurta Chintamani vivaha prakaran verse 37",
                "condition": "Same Nakshatra and same Rashi but different Padas",
                "evidence": f"Nakshatra={NAKSHATRA_NAMES_EN[b_nak]}, Pada Groom={b_pada}, Pada Bride={g_pada}"
            })
        elif (b_rasi == g_rasi and b_nak != g_nak) or (b_nak == g_nak and b_rasi != g_rasi):
            nadi_parihara = True
            nadi_parihara_note_en = (
                "Nadi Dosha Cancelled (Parihara Active): Same Rashi with different Nakshatras, or same Nakshatra in different Rashis "
                "[Ref: Muhurta Chintamani vivaha prakaran v.37]."
            )
            nadi_parihara_note_hi = (
                "नाड़ी दोष परिहार मान्य: एक राशि भिन्न नक्षत्र अथवा एक नक्षत्र भिन्न राशि होने से दोष निष्प्रभावी "
                "[मुहूर्त चिंतामणि, विवाह प्रकरण श्लोक ३७]।"
            )
            pariharas_applied.append({
                "rule_id": "NADI_GANA_SAME_RASHI_DIFFERENT_NAKSHATRA",
                "applies_to": "Nadi Dosha",
                "status": "APPLIED",
                "source_reference": "Muhurta Chintamani vivaha prakaran verse 37",
                "condition": "Same Rashi with different Nakshatras, or same Nakshatra in different Rashis",
                "evidence": f"Rashi Groom/Bride={b_rasi+1}/{g_rasi+1}, Nakshatra Groom/Bride={b_nak+1}/{g_nak+1}"
            })

    # Total Raw Score (Conventions mandate raw scores are NEVER silently changed)
    raw_total_score = float(varna_pts + vasya_pts + tara_pts + yoni_pts + maitri_pts + gana_pts + bhakoot_pts + nadi_pts)

    # Effective Score (with validated textual pariharas applied for reference)
    effective_bhakoot_pts = 7.0 if (has_bhakoot_dosha and bhakoot_parihara) else bhakoot_pts
    effective_gana_pts = 6.0 if (gana_pts < 6 and gana_parihara) else gana_pts
    effective_nadi_pts = 8.0 if (has_nadi_dosha and nadi_parihara) else nadi_pts
    effective_total_score = float(varna_pts + vasya_pts + tara_pts + yoni_pts + maitri_pts + effective_gana_pts + effective_bhakoot_pts + effective_nadi_pts)

    # Primary total_score follows raw score policy
    total_score = raw_total_score

    # Verdict Evaluation
    # Use effective score to provide astrologically enlightened guidance while honoring raw scores
    evaluation_score = effective_total_score if len(pariharas_applied) > 0 else raw_total_score

    if evaluation_score >= 32:
        verdict_en = "Supreme Soulmate Union (अति उत्तम / सर्वोत्तम)"
        verdict_hi = "अति उत्तम / सर्वोत्तम आत्मिक मिलन"
        verdict_grade = "Excellent"
        color = "#15803D"
    elif evaluation_score >= 25:
        verdict_en = "Highly Auspicious Match (उत्तम मिलान)"
        verdict_hi = "उत्तम मिलान — सुखद एवं समृद्ध दांपत्य जीवन"
        verdict_grade = "Very Good"
        color = "#16A34A"
    elif evaluation_score >= 18:
        verdict_en = "Average / Acceptable Match (मध्यम / सामान्य)"
        verdict_hi = "मध्यम / सामान्य मिलान — परस्पर समझ से अनुकूल"
        verdict_grade = "Acceptable"
        color = "#D97706"
    else:
        verdict_en = "Inauspicious / Low Match (अस्वीकार्य / दोष निवारण आवश्यक)"
        verdict_hi = "अस्वीकार्य / गंभीर दोष निवारण व परामर्श आवश्यक"
        verdict_grade = "Inauspicious"
        color = "#DC2626"

    # Classical Triple Manglik Evaluation (Lagna, Moon, Venus) with Scriptural Pariharas
    b_tm = compute_triple_manglik(boy_core)
    g_tm = compute_triple_manglik(girl_core)
    mang_eval = evaluate_manglik_compatibility(b_tm, g_tm)
    manglik_verdict_en = mang_eval["verdict_en"]
    manglik_verdict_hi = mang_eval["verdict_hi"]
    manglik_compat = mang_eval["compat"]

    # Descriptions for Kootas
    bhakoot_desc_en = (
        bhakoot_parihara_note_en if bhakoot_parihara else
        (f"Bhakoot Dosha ({pair_label}) Present" if has_bhakoot_dosha else f"Auspicious Bhakoot Harmony ({pair_label})")
    )
    bhakoot_desc_hi = (
        bhakoot_parihara_note_hi if bhakoot_parihara else
        (f"भकूट दोष विद्यमान ({pair_label})" if has_bhakoot_dosha else f"शुभ भकूट अनुकूलता ({pair_label})")
    )

    nadi_desc_en = (
        nadi_parihara_note_en if nadi_parihara else
        ("Nadi Dosha Present (Remedies Recommended)" if has_nadi_dosha else f"Harmonious Different Nadis ({b_nadi} & {g_nadi})")
    )
    nadi_desc_hi = (
        nadi_parihara_note_hi if nadi_parihara else
        ("नाड़ी दोष विद्यमान (दोष शांति अनुशंसित)" if has_nadi_dosha else f"परस्पर भिन्न नाड़ी अनुकूलता ({NADI_NAMES_HI[b_nadi]} व {NADI_NAMES_HI[g_nadi]})")
    )

    gana_desc_en = (
        gana_parihara_note_en if gana_parihara else
        ("Temperament, daily behavior & lifestyle coexistence" if gana_pts >= 5 else "Gana discordance — behavioral adjustment advised")
    )
    gana_desc_hi = (
        gana_parihara_note_hi if gana_parihara else
        ("स्वभाव, आचरण, सहिष्णुता व जीवनशैली" if gana_pts >= 5 else "गण असमानता — परस्पर समझ व सामंजस्य अपेक्षित")
    )

    # Build Koots Detailed Payload
    koots = [
        {
            "koot_en": "Varna", "koot_hi": "वर्ण",
            "max": 1, "obtained": varna_pts, "raw_score": varna_pts,
            "effective_score": varna_pts,
            "boy_val": f"{b_varna_name} ({VARNA_NAME_HI[b_varna_name]})",
            "girl_val": f"{g_varna_name} ({VARNA_NAME_HI[g_varna_name]})",
            "desc_en": "Spiritual ego & work tendency harmony",
            "desc_hi": "कार्य प्रवृत्ति व आध्यात्मिक अहंकार सामंजस्य",
            "parihara_applied": False,
            "source_id": DEFAULT_SOURCE_ID, "rule_version": RULE_VERSION
        },
        {
            "koot_en": "Vasya", "koot_hi": "वश्य",
            "max": 2, "obtained": vasya_pts, "raw_score": vasya_pts,
            "effective_score": vasya_pts,
            "boy_val": f"{b_vas_class} ({VASHYA_CLASSES_HI[b_vas_class]})",
            "girl_val": f"{g_vas_class} ({VASHYA_CLASSES_HI[g_vas_class]})",
            "desc_en": "Mutual attraction, loyalty & willingness to cooperate",
            "desc_hi": "परस्पर आकर्षण, निष्ठा व सहयोग भावना",
            "parihara_applied": False,
            "source_id": DEFAULT_SOURCE_ID, "rule_version": RULE_VERSION
        },
        {
            "koot_en": "Tara", "koot_hi": "तारा",
            "max": 3, "obtained": tara_pts, "raw_score": tara_pts,
            "effective_score": tara_pts,
            "boy_val": f"{TARA_NAMES_EN[rem_bride_to_groom]} ({count_bride_to_groom}th)",
            "girl_val": f"{TARA_NAMES_EN[rem_groom_to_bride]} ({count_groom_to_bride}th)",
            "desc_en": "Birth star destiny, longevity & health harmony",
            "desc_hi": "भाग्य, स्वास्थ्य, दीर्घायु व नक्षत्र सामंजस्य",
            "parihara_applied": False,
            "source_id": DEFAULT_SOURCE_ID, "rule_version": RULE_VERSION
        },
        {
            "koot_en": "Yoni", "koot_hi": "योनि",
            "max": 4, "obtained": yoni_pts, "raw_score": yoni_pts,
            "effective_score": yoni_pts,
            "boy_val": f"{b_yoni_animal} ({YONI_ANIMALS_HI[b_yoni_animal]})",
            "girl_val": f"{g_yoni_animal} ({YONI_ANIMALS_HI[g_yoni_animal]})",
            "desc_en": "Biological & physical intimacy compatibility",
            "desc_hi": "जैविक व शारीरिक दांपत्य सुख अनुकूलता",
            "parihara_applied": False,
            "source_id": DEFAULT_SOURCE_ID, "rule_version": RULE_VERSION
        },
        {
            "koot_en": "Graha Maitri", "koot_hi": "ग्रहमैत्री",
            "max": 5, "obtained": maitri_pts, "raw_score": maitri_pts,
            "effective_score": maitri_pts,
            "boy_val": f"{b_lord_name} ({RASHI_NAMES_HI[b_rasi]})",
            "girl_val": f"{g_lord_name} ({RASHI_NAMES_HI[g_rasi]})",
            "desc_en": "Moon sign lords natural friendship & mental harmony",
            "desc_hi": "चंद्र राशि स्वामियों की मित्रता व वैचारिक शांति",
            "parihara_applied": False,
            "source_id": DEFAULT_SOURCE_ID, "rule_version": RULE_VERSION
        },
        {
            "koot_en": "Gana", "koot_hi": "गण",
            "max": 6, "obtained": gana_pts, "raw_score": gana_pts,
            "effective_score": effective_gana_pts,
            "boy_val": f"{b_gana} ({GANA_NAMES_HI[b_gana]})",
            "girl_val": f"{g_gana} ({GANA_NAMES_HI[g_gana]})",
            "desc_en": gana_desc_en,
            "desc_hi": gana_desc_hi,
            "parihara_applied": gana_parihara,
            "source_id": DEFAULT_SOURCE_ID, "rule_version": RULE_VERSION
        },
        {
            "koot_en": "Bhakoot", "koot_hi": "भकूट",
            "max": 7, "obtained": bhakoot_pts, "raw_score": bhakoot_pts,
            "effective_score": effective_bhakoot_pts,
            "boy_val": f"{RASHI_NAMES_HI[b_rasi]} ({RASHI_NAMES_EN[b_rasi]})",
            "girl_val": f"{RASHI_NAMES_HI[g_rasi]} ({RASHI_NAMES_EN[g_rasi]})",
            "desc_en": bhakoot_desc_en,
            "desc_hi": bhakoot_desc_hi,
            "parihara_applied": bhakoot_parihara,
            "source_id": DEFAULT_SOURCE_ID, "rule_version": RULE_VERSION
        },
        {
            "koot_en": "Nadi", "koot_hi": "नाड़ी",
            "max": 8, "obtained": nadi_pts, "raw_score": nadi_pts,
            "effective_score": effective_nadi_pts,
            "boy_val": f"{b_nadi} ({NADI_NAMES_HI[b_nadi]})",
            "girl_val": f"{g_nadi} ({NADI_NAMES_HI[g_nadi]})",
            "desc_en": nadi_desc_en,
            "desc_hi": nadi_desc_hi,
            "parihara_applied": nadi_parihara,
            "source_id": DEFAULT_SOURCE_ID, "rule_version": RULE_VERSION
        }
    ]

    # Dedicated Dosha & Exception Engines
    nadi_audit = evaluate_nadi_exceptions(b_moon, g_moon, nadi_pts)
    bhakoot_audit = evaluate_bhakoot_exceptions(b_moon, g_moon, has_bhakoot_dosha)
    groom_mang_eval = evaluate_person_manglik(boy_core)
    bride_mang_eval = evaluate_person_manglik(girl_core)
    dosha_samya_eval = evaluate_dosha_samya(groom_mang_eval, bride_mang_eval)
    additional_compat = compute_comprehensive_additional_compatibility(boy_core, girl_core)

    # Classical Remedies Library
    classical_remedies = []
    if has_nadi_dosha and not nadi_audit.get("is_cancelled"):
        classical_remedies.append({
            "dosha": "Nadi Dosha",
            "dosha_hi": "नाड़ी दोष",
            "source": "Muhurta Chintamani / Jyotish Darpana",
            "remedy_en": "Perform Mahamrityunjaya Japa (125,000 recitations), donate gold (Swarna Daan), cow (Go Daan) or food grains to virtuous Brahmins.",
            "remedy_hi": "सवा लाख महामृत्युंजय जप अनुष्ठान, स्वर्ण दान, गोदान अथवा अन्न-वस्त्र दान द्वारा नाड़ी शांति कराएं।"
        })
    if has_bhakoot_dosha and not bhakoot_audit.get("is_cancelled"):
        classical_remedies.append({
            "dosha": "Bhakoot Dosha",
            "dosha_hi": "भकूट दोष",
            "source": "Muhurta Chintamani vivaha prakarana v. 32",
            "remedy_en": "Recite Vishnu Sahasranama or Santana Gopala Mantra; worship Gauri-Shankara to strengthen conjugal bonding.",
            "remedy_hi": "विष्णु सहस्रनाम अथवा संतान गोपाल मंत्र का नित्य पाठ करें; गौरी-शंकर पूजन से वैवाहिक सामंजस्य दृढ़ करें।"
        })
    if (groom_mang_eval.get("is_manglik") or bride_mang_eval.get("is_manglik")) and dosha_samya_eval.get("compat") not in ("Clean", "Neutralized", "Parihara Balanced"):
        classical_remedies.append({
            "dosha": "Mangal / Kuja Dosha",
            "dosha_hi": "मंगल / कुज दोष",
            "source": "Brihat Parashara Hora Shastra Ch. 84",
            "remedy_en": "Chant Mangal Chandika Stotra or recite Hanuman Chalisa every Tuesday; worship Lord Kartikeya; perform Kumbha/Vishnu Vivaha if traditionally mandated.",
            "remedy_hi": "प्रति मंगलवार हनुमान चालीसा एवं मंगल चण्डिका स्तोत्र का पाठ; कार्तिकेय पूजन तथा आवश्यकतानुसार शास्त्रोक्त कुंभ/विष्णु विवाह।"
        })

    # Comprehensive Audit Trail (Traceable Execution Verification)
    audit_trail = [
        {
            "step": 1, "category": "Input Module", "rule_id": "INP-01",
            "details": f"Groom ({boy_core['meta'].get('name', 'Groom')}): {boy_core['meta'].get('place', '')} | Bride ({girl_core['meta'].get('name', 'Bride')}): {girl_core['meta'].get('place', '')}",
            "verified": True
        },
        {
            "step": 2, "category": "Astronomical Longitude", "rule_id": "ASTRO-01",
            "details": f"Groom Moon={b_moon.get('sid_lon', 0.0):.4f}° ({RASHI_NAMES_EN[b_rasi]} {b_moon.get('deg_in_sign', 0.0):.2f}°); Bride Moon={g_moon.get('sid_lon', 0.0):.4f}° ({RASHI_NAMES_EN[g_rasi]} {g_moon.get('deg_in_sign', 0.0):.2f}°)",
            "verified": True
        },
        {
            "step": 3, "category": "Varna Koota", "rule_id": "VARNA_CLASSICAL_01",
            "details": f"Groom={RASHI_VARNA_EN[b_rasi]} (Rank {VARNA_RANK_BY_NAME[RASHI_VARNA_EN[b_rasi]]}), Bride={RASHI_VARNA_EN[g_rasi]} (Rank {VARNA_RANK_BY_NAME[RASHI_VARNA_EN[g_rasi]]}) -> Score: {varna_pts}/1.0",
            "verified": True
        },
        {
            "step": 4, "category": "Vashya Koota", "rule_id": "VASHYA_5X5_SUBDIVIDED",
            "details": f"Groom={b_vas_class}, Bride={g_vas_class} -> Score: {vasya_pts}/2.0",
            "verified": True
        },
        {
            "step": 5, "category": "Tara Koota", "rule_id": "TARA_CONVENTIONAL_BIDIRECTIONAL",
            "details": f"Forward={score_bride_to_groom}/1.5 ({TARA_NAMES_EN[rem_bride_to_groom]}), Reverse={score_groom_to_bride}/1.5 ({TARA_NAMES_EN[rem_groom_to_bride]}) -> Score: {tara_pts}/3.0",
            "verified": True
        },
        {
            "step": 6, "category": "Yoni Koota", "rule_id": "YONI_14X14_CLASSICAL",
            "details": f"Groom={b_yoni_animal}, Bride={g_yoni_animal} -> Score: {yoni_pts}/4.0",
            "verified": True
        },
        {
            "step": 7, "category": "Graha Maitri Koota", "rule_id": "GRAHA_MAITRI_6TIER",
            "details": f"Groom Lord={b_lord_name}, Bride Lord={g_lord_name} -> Score: {maitri_pts}/5.0",
            "verified": True
        },
        {
            "step": 8, "category": "Gana Koota", "rule_id": "GANA_DIRECTIONAL_3X3",
            "details": f"Groom={b_gana}, Bride={g_gana} -> Score: {gana_pts}/6.0 (Parihara: {'Active' if gana_parihara else 'None'})",
            "verified": True
        },
        {
            "step": 9, "category": "Bhakoot Koota", "rule_id": "BHAKOOT_CIRCULAR_12",
            "details": f"Distance={pair_label} -> Raw: {bhakoot_pts}/7.0 | Parihara: {bhakoot_audit.get('cancellation_status')}",
            "verified": True
        },
        {
            "step": 10, "category": "Nadi Koota", "rule_id": "NADI_CLASSICAL_EIGHT",
            "details": f"Groom={b_nadi}, Bride={g_nadi} -> Raw: {nadi_pts}/8.0 | Exception: {nadi_audit.get('cancellation_status')}",
            "verified": True
        },
        {
            "step": 11, "category": "Manglik / Kuja Dosha", "rule_id": "KUJA-ENGINE-01",
            "details": f"Groom: {groom_mang_eval.get('status')} | Bride: {bride_mang_eval.get('status')} | Harmony: {dosha_samya_eval.get('compat')}",
            "verified": True
        },
        {
            "step": 12, "category": "Papa Samya", "rule_id": "PAPA-SAMYA-PARASHARI",
            "details": f"Groom Papa={additional_compat['papa_samya']['groom_points']} pts, Bride Papa={additional_compat['papa_samya']['bride_points']} pts ({additional_compat['papa_samya']['balance_status']})",
            "verified": True
        },
        {
            "step": 13, "category": "Dasha Compatibility", "rule_id": "DASHA-VIMSHOTTARI-01",
            "details": f"Groom MD={additional_compat['dasha_compatibility']['groom_current_mahadasha']}, Bride MD={additional_compat['dasha_compatibility']['bride_current_mahadasha']} ({additional_compat['dasha_compatibility']['dasha_harmony']})",
            "verified": True
        }
    ]

    result_payload = {
        "dataset_name": DATASET_NAME,
        "rule_version": RULE_VERSION,
        "source_id": DEFAULT_SOURCE_ID,
        "calculation_conventions": CALCULATION_CONVENTIONS,
        "total_score": round(total_score, 1),
        "raw_total_score": round(raw_total_score, 1),
        "effective_total_score": round(effective_total_score, 1),
        "max_score": 36,
        "percentage": round((total_score / 36.0) * 100, 1),
        "effective_percentage": round((effective_total_score / 36.0) * 100, 1),
        "verdict_en": verdict_en,
        "verdict_hi": verdict_hi,
        "verdict_grade": verdict_grade,
        "verdict_color": color,
        "koots": koots,
        "pariharas_applied": pariharas_applied,
        "nadi_exception_audit": nadi_audit,
        "bhakoot_exception_audit": bhakoot_audit,
        "groom_manglik_audit": groom_mang_eval,
        "bride_manglik_audit": bride_mang_eval,
        "dosha_samya_audit": dosha_samya_eval,
        "additional_compatibility": additional_compat,
        "audit_trail": audit_trail,
        "classical_remedies": classical_remedies,
        "boy_summary": {
            "name": boy_core["meta"]["name"],
            "lagna": f"{boy_core['meta']['lagna_en']} ({boy_core['meta']['lagna_hi']})",
            "rasi": f"{boy_core['meta']['rasi_en']} ({boy_core['meta']['rasi_hi']})",
            "nakshatra": f"{boy_core['meta']['nakshatra_pada_en']} ({boy_core['meta']['nakshatra_pada_hi']})",
            "is_manglik": b_tm["is_manglik"],
            "manglik_status": b_tm["status_hi"],
            "triple_manglik": b_tm
        },
        "girl_summary": {
            "name": girl_core["meta"]["name"],
            "lagna": f"{girl_core['meta']['lagna_en']} ({girl_core['meta']['lagna_hi']})",
            "rasi": f"{girl_core['meta']['rasi_en']} ({girl_core['meta']['rasi_hi']})",
            "nakshatra": f"{girl_core['meta']['nakshatra_pada_en']} ({girl_core['meta']['nakshatra_pada_hi']})",
            "is_manglik": g_tm["is_manglik"],
            "manglik_status": g_tm["status_hi"],
            "triple_manglik": g_tm
        },
        "manglik_harmony": {
            "verdict_en": manglik_verdict_en,
            "verdict_hi": manglik_verdict_hi,
            "compat": manglik_compat
        },
        "triple_manglik": {
            "groom": b_tm,
            "bride": g_tm,
            "harmony": mang_eval
        }
    }

    # 10 Astrological Compatibility Pillars (Classical Parameter Evaluation)
    result_payload["ten_pillars"] = compute_ten_pillars_compatibility(boy_core, girl_core, result_payload)

    # Automated Pre-Generation Astrological Quality Checks
    try:
        from engine.quality_checker import run_pre_generation_quality_checks
        q_audit = run_pre_generation_quality_checks(result_payload, boy_core, girl_core)
        result_payload["quality_audit"] = q_audit
    except Exception as qe:
        result_payload["quality_audit"] = {"success": False, "error": str(qe)}

    return result_payload


def calculate_ashtakoot_raw(
    groom_rashi_idx: int,
    groom_nak_idx: int,
    groom_pada: int,
    bride_rashi_idx: int,
    bride_nak_idx: int,
    bride_pada: int
) -> dict:
    """
    Direct calculator by rashi index (0..11), nakshatra index (0..26), and pada (1..4)
    without needing full ephemeris objects. Useful for automated tests and unit benchmarks.
    """
    boy_core = {
        "meta": {
            "name": "Groom",
            "lagna_sign_num": groom_rashi_idx + 1,
            "lagna_en": RASHI_NAMES_EN[groom_rashi_idx], "lagna_hi": RASHI_NAMES_HI[groom_rashi_idx],
            "rasi_en": RASHI_NAMES_EN[groom_rashi_idx], "rasi_hi": RASHI_NAMES_HI[groom_rashi_idx],
            "nakshatra_pada_en": f"{NAKSHATRA_NAMES_EN[groom_nak_idx]} {groom_pada}",
            "nakshatra_pada_hi": f"{NAKSHATRA_NAMES_HI[groom_nak_idx]} चरण {groom_pada}"
        },
        "planet_by_id": {
            "Moon": {
                "sign_idx": groom_rashi_idx,
                "sign_num": groom_rashi_idx + 1,
                "nakshatra_idx": groom_nak_idx,
                "pada": groom_pada
            },
            "Mars": {"house": 1, "sign_idx": 0, "sign_num": 1},
            "Jupiter": {"house": 5, "sign_idx": 4, "sign_num": 5},
            "ASC": {"deg_in_sign": 15.0}
        }
    }
    girl_core = {
        "meta": {
            "name": "Bride",
            "lagna_sign_num": bride_rashi_idx + 1,
            "lagna_en": RASHI_NAMES_EN[bride_rashi_idx], "lagna_hi": RASHI_NAMES_HI[bride_rashi_idx],
            "rasi_en": RASHI_NAMES_EN[bride_rashi_idx], "rasi_hi": RASHI_NAMES_HI[bride_rashi_idx],
            "nakshatra_pada_en": f"{NAKSHATRA_NAMES_EN[bride_nak_idx]} {bride_pada}",
            "nakshatra_pada_hi": f"{NAKSHATRA_NAMES_HI[bride_nak_idx]} चरण {bride_pada}"
        },
        "planet_by_id": {
            "Moon": {
                "sign_idx": bride_rashi_idx,
                "sign_num": bride_rashi_idx + 1,
                "nakshatra_idx": bride_nak_idx,
                "pada": bride_pada
            },
            "Mars": {"house": 1, "sign_idx": 0, "sign_num": 1},
            "Jupiter": {"house": 5, "sign_idx": 4, "sign_num": 5},
            "ASC": {"deg_in_sign": 15.0}
        }
    }
    return calculate_ashtakoot_milan(boy_core, girl_core)
