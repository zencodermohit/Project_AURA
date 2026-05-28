"""
ai_service.py - Core AI/NLP Aura Analysis Engine

This module provides the core aura and personality analysis functionality
for the Project AURA pipeline. It uses TextBlob for basic sentiment analysis,
NLTK for tokenization, lemmatization, and stopword removal, and VADER for
compound sentiment scoring.

The module maps user-provided text to one of 8 aura personality profiles,
computes energy scores, confidence metrics, and extracts detected keywords.

Dependencies:
    - textblob
    - nltk (punkt_tab, averaged_perceptron_tagger_eng, stopwords, wordnet)
    - vaderSentiment
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Download required NLTK data at module load time
# ---------------------------------------------------------------------------
_NLTK_RESOURCES = [
    "punkt_tab",
    "averaged_perceptron_tagger_eng",
    "stopwords",
    "wordnet",
]

for _resource in _NLTK_RESOURCES:
    try:
        nltk.download(_resource, quiet=True)
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to download NLTK resource '%s': %s", _resource, exc)

# ---------------------------------------------------------------------------
# Aura profile definitions
# ---------------------------------------------------------------------------
AURA_PROFILES: dict[str, dict[str, Any]] = {
    "Visionary": {
        "keywords": [
            "dream", "future", "create", "imagine", "innovate", "vision", "inspire",
            "invent", "pioneer", "transform", "revolutionary", "futuristic", "build",
            "design", "creative", "idea", "possibility", "forward",
        ],
        "color": "#9B59B6",
        "energy_level": "High Creative Energy",
        "traits": [
            "imaginative", "future-focused", "emotionally expressive",
            "innovative", "inspired",
        ],
    },
    "Strategic": {
        "keywords": [
            "logic", "plan", "system", "efficiency", "optimize", "strategy", "analyze",
            "structure", "organize", "framework", "method", "process", "goal",
            "objective", "tactical", "systematic", "calculate", "precise",
        ],
        "color": "#3498DB",
        "energy_level": "Focused Analytical Energy",
        "traits": [
            "logical", "methodical", "goal-oriented", "structured", "efficient",
        ],
    },
    "Calm Sage": {
        "keywords": [
            "peace", "calm", "wisdom", "patience", "balance", "mindful", "serene",
            "tranquil", "harmony", "meditate", "reflect", "quiet", "gentle",
            "steady", "centered", "grounded", "still", "wise",
        ],
        "color": "#1ABC9C",
        "energy_level": "Balanced Harmonious Energy",
        "traits": [
            "patient", "wise", "balanced", "mindful", "grounded",
        ],
    },
    "Rebel Creator": {
        "keywords": [
            "break", "disrupt", "rebel", "bold", "challenge", "defy", "radical",
            "unconventional", "fierce", "riot", "freedom", "resist", "revolution",
            "fearless", "daring", "wild", "untamed", "provocative",
        ],
        "color": "#E74C3C",
        "energy_level": "Intense Disruptive Energy",
        "traits": [
            "bold", "unconventional", "fearless", "provocative", "daring",
        ],
    },
    "Analytical Thinker": {
        "keywords": [
            "analyze", "data", "research", "detail", "precise", "method", "evidence",
            "hypothesis", "experiment", "observe", "measure", "quantify", "study",
            "investigate", "evaluate", "assess", "science", "technical",
        ],
        "color": "#5DADE2",
        "energy_level": "Deep Intellectual Energy",
        "traits": [
            "detail-oriented", "curious", "systematic", "evidence-based", "precise",
        ],
    },
    "Empathic Soul": {
        "keywords": [
            "feel", "care", "kind", "empathy", "love", "compassion", "heart",
            "nurture", "support", "understand", "connect", "warm", "tender",
            "sensitive", "emotional", "gentle", "heal", "comfort",
        ],
        "color": "#2ECC71",
        "energy_level": "Warm Nurturing Energy",
        "traits": [
            "compassionate", "empathetic", "nurturing", "warm-hearted", "sensitive",
        ],
    },
    "Ambitious Leader": {
        "keywords": [
            "lead", "achieve", "power", "success", "drive", "ambition", "conquer",
            "dominate", "influence", "command", "authority", "victory", "win",
            "excel", "champion", "determination", "strong", "unstoppable",
        ],
        "color": "#F39C12",
        "energy_level": "Powerful Commanding Energy",
        "traits": [
            "determined", "ambitious", "influential", "confident", "driven",
        ],
    },
    "Mystic Dreamer": {
        "keywords": [
            "mystery", "cosmic", "spiritual", "intuition", "ethereal", "mystic",
            "soul", "universe", "divine", "transcend", "astral", "destiny",
            "magical", "enchanted", "otherworldly", "celestial", "supernatural", "aura",
        ],
        "color": "#00BCD4",
        "energy_level": "Ethereal Cosmic Energy",
        "traits": [
            "intuitive", "spiritual", "mysterious", "transcendent", "cosmic-minded",
        ],
    },
}

# Pre-initialise reusable NLP objects
_vader_analyzer = SentimentIntensityAnalyzer()
_lemmatizer = WordNetLemmatizer()
_stop_words: set[str] = set(stopwords.words("english"))


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_energy_description(score: int) -> str:
    """Return a human-readable energy description for a numeric score.

    Args:
        score: An energy score in the range 0-100.

    Returns:
        A descriptive string corresponding to the score bracket.
    """
    if score <= 20:
        return "Low"
    if score <= 40:
        return "Moderate"
    if score <= 60:
        return "High"
    if score <= 80:
        return "Very High"
    return "Extraordinary"


# ---------------------------------------------------------------------------
# Core analysis function
# ---------------------------------------------------------------------------

def analyze_personality(text: str) -> dict[str, Any]:
    """Analyse free-form text and produce a structured aura/personality profile.

    The function performs the following steps:
        1. Normalises the input text to lowercase.
        2. Computes TextBlob polarity & subjectivity.
        3. Computes VADER compound sentiment score.
        4. Tokenises, removes stopwords & non-alpha tokens, and lemmatises.
        5. Scores each aura profile by keyword matches (direct + lemmatised).
        6. Selects the top-scoring aura (defaults to *Mystic Dreamer*).
        7. Derives energy_score (0-100) and confidence_score (0-100%).
        8. Extracts the list of detected keywords.

    Args:
        text: The raw user-provided text to analyse.

    Returns:
        A dictionary containing the full analysis result::

            {
                "aura_type": str,
                "aura_color": str,
                "energy_level": str,
                "personality_traits": list[str],
                "energy_score": int,
                "confidence_score": int,
                "sentiment": {
                    "polarity": float,
                    "subjectivity": float,
                    "compound": float,
                },
                "keywords_detected": list[str],
                "timestamp": str,   # ISO-8601 format
            }
    """
    # --- Step 1: normalise ------------------------------------------------
    lower_text: str = text.lower()

    # --- Step 2: TextBlob sentiment --------------------------------------
    blob = TextBlob(lower_text)
    polarity: float = round(blob.sentiment.polarity, 4)
    subjectivity: float = round(blob.sentiment.subjectivity, 4)

    # --- Step 3: VADER compound score ------------------------------------
    vader_scores: dict[str, float] = _vader_analyzer.polarity_scores(lower_text)
    compound: float = round(vader_scores["compound"], 4)

    # --- Step 4: tokenise, filter, lemmatise -----------------------------
    try:
        tokens: list[str] = word_tokenize(lower_text)
    except LookupError:
        # Fallback to naive whitespace split if tokenizer data is missing
        logger.warning("NLTK tokenizer data unavailable; falling back to split().")
        tokens = lower_text.split()

    filtered_tokens: list[str] = [
        tok for tok in tokens if tok.isalpha() and tok not in _stop_words
    ]

    lemmatised_tokens: list[str] = [
        _lemmatizer.lemmatize(tok) for tok in filtered_tokens
    ]

    # Build combined token set for matching (both raw filtered and lemmatised)
    token_set: set[str] = set(filtered_tokens) | set(lemmatised_tokens)

    # --- Step 5: score each aura profile ---------------------------------
    aura_scores: dict[str, int] = {}
    aura_matched_keywords: dict[str, list[str]] = {}

    for aura_name, profile in AURA_PROFILES.items():
        matched: list[str] = []
        for keyword in profile["keywords"]:
            # Direct match in token set
            if keyword in token_set:
                matched.append(keyword)
            else:
                # Also check lemmatised form of the keyword itself
                lemma_kw = _lemmatizer.lemmatize(keyword)
                if lemma_kw != keyword and lemma_kw in token_set:
                    matched.append(keyword)

        aura_scores[aura_name] = len(matched)
        aura_matched_keywords[aura_name] = matched

    # --- Step 6: pick top aura (default Mystic Dreamer) ------------------
    max_score: int = max(aura_scores.values()) if aura_scores else 0

    if max_score > 0:
        best_aura: str = max(aura_scores, key=lambda k: aura_scores[k])
    else:
        best_aura = "Mystic Dreamer"

    profile_data: dict[str, Any] = AURA_PROFILES[best_aura]

    # --- Step 7: energy_score & confidence_score -------------------------
    # Energy score (0-100): driven by sentiment intensity + keyword density
    sentiment_intensity: float = abs(compound)
    keyword_density: float = (
        len(aura_matched_keywords.get(best_aura, [])) / max(len(filtered_tokens), 1)
    )
    raw_energy: float = (sentiment_intensity * 50) + (keyword_density * 50)
    energy_score: int = max(0, min(100, int(round(raw_energy))))

    # Confidence score (0-100%): match strength + text length factor
    match_strength: float = max_score / max(len(profile_data["keywords"]), 1)
    text_length_factor: float = min(len(filtered_tokens) / 50.0, 1.0)
    raw_confidence: float = (match_strength * 70) + (text_length_factor * 30)
    confidence_score: int = max(0, min(100, int(round(raw_confidence))))

    # --- Step 8: detected keywords ---------------------------------------
    keywords_detected: list[str] = sorted(
        set(aura_matched_keywords.get(best_aura, []))
    )

    # --- Build result dict -----------------------------------------------
    result: dict[str, Any] = {
        "aura_type": best_aura,
        "aura_color": profile_data["color"],
        "energy_level": profile_data["energy_level"],
        "personality_traits": list(profile_data["traits"]),
        "energy_score": energy_score,
        "confidence_score": confidence_score,
        "sentiment": {
            "polarity": polarity,
            "subjectivity": subjectivity,
            "compound": compound,
        },
        "keywords_detected": keywords_detected,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "Aura analysis complete — type=%s, energy=%d, confidence=%d%%",
        best_aura,
        energy_score,
        confidence_score,
    )

    return result


# ===========================================================================
# MBTI & CAMERA PHOTO AURA EXTENSION
# ===========================================================================

import io
from PIL import Image, ImageStat

# Curated 20 questions mapping to MBTI dimensions
# Scoring: 1 (Strongly Disagree) to 5 (Strongly Agree) -> Mapped to -2 to +2
# Direction: 1 means Agree favors positive letter, -1 means Agree favors negative letter
MBTI_QUESTIONS: list[dict[str, Any]] = [
    # Questions are shuffled across dimensions. The scoring map below defines
    # which dimension each question truly measures, and the direction of scoring.
    # direction +1 = agree pushes toward the FIRST letter (E, S, T, J)
    # direction -1 = agree pushes toward the SECOND letter (I, N, F, P)

    # q1: "honest truth vs protect feelings" -> Thinking (+1)
    {"id": "q1", "dimension": "TF", "direction": 1},
    # q2: "pack the night before" -> Perceiving (-1 on JP scale)
    {"id": "q2", "dimension": "JP", "direction": -1},
    # q3: "Friday night involves other people" -> Extraversion (+1)
    {"id": "q3", "dimension": "EI", "direction": 1},
    # q4: "zone out into a thought chain" -> Intuition (-1 on SN scale)
    {"id": "q4", "dimension": "SN", "direction": -1},
    # q5: "hard to enjoy movie with plot holes" -> Thinking (+1)
    {"id": "q5", "dimension": "TF", "direction": 1},
    # q6: "think out loud, best ideas from talking" -> Extraversion (+1)
    {"id": "q6", "dimension": "EI", "direction": 1},
    # q7: "notice crooked frame / hairstyle change" -> Sensing (+1)
    {"id": "q7", "dimension": "SN", "direction": 1},
    # q8: "satisfaction when to-do list is checked off" -> Judging (+1)
    {"id": "q8", "dimension": "JP", "direction": 1},
    # q9: "alone all weekend sounds refreshing" -> Introversion (-1)
    {"id": "q9", "dimension": "EI", "direction": -1},
    # q10: "more interested in what could exist" -> Intuition (-1)
    {"id": "q10", "dimension": "SN", "direction": -1},
    # q11: "understand both sides logically in a fight" -> Thinking (+1)
    {"id": "q11", "dimension": "TF", "direction": 1},
    # q12: "unexpected changes excite you" -> Perceiving (-1)
    {"id": "q12", "dimension": "JP", "direction": -1},
    # q13: "recharge by going somewhere crowded" -> Extraversion (+1)
    {"id": "q13", "dimension": "EI", "direction": 1},
    # q14: "trust gut feeling with no logical reason" -> Intuition (-1)
    {"id": "q14", "dimension": "SN", "direction": -1},
    # q15: "world would be better if people relied on reason" -> Thinking (+1)
    {"id": "q15", "dimension": "TF", "direction": 1},
    # q16: "prefer keeping options open" -> Perceiving (-1)
    {"id": "q16", "dimension": "JP", "direction": -1},
    # q17: "process thoughts internally, share only conclusion" -> Introversion (-1)
    {"id": "q17", "dimension": "EI", "direction": -1},
    # q18: "rather master a proven skill than experiment" -> Sensing (+1)
    {"id": "q18", "dimension": "SN", "direction": 1},
    # q19: "easily absorb emotions of people around you" -> Feeling (-1)
    {"id": "q19", "dimension": "TF", "direction": -1},
    # q20: "messy workspace with an internal system" -> Perceiving (-1)
    {"id": "q20", "dimension": "JP", "direction": -1},
]

# Rich MBTI personality profiles (16 types)
MBTI_PROFILES: dict[str, dict[str, Any]] = {
    "INTJ": {
        "title": "The Future Griever",
        "color": "#9B59B6",
        "energy_level": "Deep Strategic Energy",
        "traits": ["analytical", "independent", "determined", "ambitious"],
        "description": "You mourn future outcomes before they happen. You mentally simulate conversations so much that real conversations feel slow. You appear emotionally cold because you compress emotions into analysis. You disappear completely when overwhelmed instead of asking for help. You trust competence faster than kindness.",
        "careers": ["Systems Engineer", "Software Architect", "Strategic Planner", "Investment Banker"],
        "famous_people": ["Elon Musk", "Nikola Tesla", "Michelle Obama", "Friedrich Nietzsche"],
        "romantic_compatible": ["Intellectually stimulating debaters", "Independent visionaries", "People who respect personal space"]
    },
    "INTP": {
        "title": "The Emotional Archivist",
        "color": "#4A90E2",
        "energy_level": "Quiet Intellectual Energy",
        "traits": ["analytical", "curious", "objective", "unconventional"],
        "description": "You remember emotional humiliation with almost photographic clarity. You rehearse conversations alone afterward for hours. Your room may look chaotic, but you know where everything is conceptually. You become extremely loyal once someone respects your intellectual independence. Deep down, you secretly fear becoming ordinary more than failing.",
        "careers": ["Data Scientist", "Research Analyst", "Philosopher", "Security Analyst"],
        "famous_people": ["Albert Einstein", "Marie Curie", "Bill Gates", "Isaac Newton"],
        "romantic_compatible": ["Open-minded explorers", "Patient listeners", "Partners who enjoy deep theoretical conversations"]
    },
    "ENTJ": {
        "title": "The Exhausted Commander",
        "color": "#C0392B",
        "energy_level": "Powerful Directing Energy",
        "traits": ["assertive", "efficient", "driven", "strategic"],
        "description": "You measure love through competence and reliability, not words. You can become deeply depressed when you lose momentum or direction. You secretly envy carefree people. You frequently overestimate how emotionally resilient others are. Your biggest insecurity is irrelevance — not failure.",
        "careers": ["Project Manager", "CEO / Executive", "Management Consultant", "Venture Capitalist"],
        "famous_people": ["Steve Jobs", "Margaret Thatcher", "Franklin D. Roosevelt", "Gordon Ramsay"],
        "romantic_compatible": ["Driven and ambitious partners", "People who appreciate direct honesty", "Supportive confidants"]
    },
    "ENTP": {
        "title": "The Hidden Self-Saboteur",
        "color": "#E67E22",
        "energy_level": "Vibrant Disruptive Energy",
        "traits": ["creative", "witty", "curious", "bold"],
        "description": "You argue against your own beliefs just to test reality. You can accidentally manipulate people without intending to because you naturally see psychological weak points. You become quiet and detached during emotional pain instead of dramatic. You get addicted to potential energy more than achievement itself — and you frequently abandon projects right before success because finishing removes possibility space.",
        "careers": ["Product Innovator", "Entrepreneur", "Creative Director", "Systems Designer"],
        "famous_people": ["Mark Twain", "Thomas Edison", "Tom Hanks", "Celine Dion"],
        "romantic_compatible": ["Intellectual sparring partners", "Spontaneous adventurers", "People with a sharp sense of humor"]
    },
    "INFJ": {
        "title": "The Human Contradiction",
        "color": "#1ABC9C",
        "energy_level": "Ethereal Harmonious Energy",
        "traits": ["idealistic", "principled", "insightful", "visionary"],
        "description": "You feel simultaneously detached from people and obsessed with understanding them. You predict relationship endings months early but stay anyway. You can suddenly door-slam people after tolerating too much for too long. You often feel older than your age mentally. Your intuition works so fast you cannot explain how you know something.",
        "careers": ["Clinical Counselor", "Environmentalist", "Writer", "Nurturing Advisor"],
        "famous_people": ["Martin Luther King Jr.", "Nelson Mandela", "Mother Teresa", "Lady Gaga"],
        "romantic_compatible": ["Authentic and genuine souls", "Deeply empathetic listeners", "Partners who value meaningful connection"]
    },
    "INFP": {
        "title": "The Silent Intensity",
        "color": "#2ECC71",
        "energy_level": "Warm Nurturing Energy",
        "traits": ["idealistic", "sensitive", "creative", "harmonious"],
        "description": "You appear calm while feeling emotions at extreme intensity internally. You attach memories to songs more strongly than most people. You disappear from people you love when emotionally overwhelmed. You have an internal moral system stronger than any external rules. You frequently feel guilty for not becoming who you imagined you could be.",
        "careers": ["Creative Writer", "Psychotherapist", "Artist", "Humanitarian Worker"],
        "famous_people": ["William Shakespeare", "Vincent van Gogh", "Princess Diana", "Keanu Reeves"],
        "romantic_compatible": ["Gentle and romantic partners", "People who appreciate art and beauty", "Loyal and supportive confidants"]
    },
    "ENFJ": {
        "title": "The Emotional Strategist",
        "color": "#F1C40F",
        "energy_level": "Radiant Charismatic Energy",
        "traits": ["charismatic", "inspiring", "altruistic", "confident"],
        "description": "You can read social hierarchy unusually fast. You know how someone feels before they say it. You sometimes over-help others to avoid facing your own emotional needs. You can become frighteningly persuasive when emotionally convinced. Your burnout is invisible because you keep functioning while collapsing internally.",
        "careers": ["Public Relations Specialist", "Teacher / Educator", "Community Organizer", "Nonprofit Executive"],
        "famous_people": ["Barack Obama", "Oprah Winfrey", "John Malovich", "Malala Yousafzai"],
        "romantic_compatible": ["People who appreciate active encouragement", "Partners who value deep emotional bonds", "Driven but compassionate souls"]
    },
    "ENFP": {
        "title": "The Identity Shape-Shifter",
        "color": "#27AE60",
        "energy_level": "High Creative Spark",
        "traits": ["enthusiastic", "creative", "social", "independent"],
        "description": "You unconsciously mirror personalities around you. People only see your fun layer, so you often feel deeply misunderstood. You can suddenly become hyper-serious after emotional betrayal. You predict emotional outcomes before logical ones. Your biggest battle is always discipline versus inspiration.",
        "careers": ["Marketing Director", "Event Producer", "Journalist", "Creative Designer"],
        "famous_people": ["Walt Disney", "Robin Williams", "Quentin Tarantino", "Robert Downey Jr."],
        "romantic_compatible": ["Imaginative dreamers", "Partners who love spontaneous travel", "People who embrace emotional depth"]
    },
    "ISTJ": {
        "title": "The Memory Guardian",
        "color": "#34495E",
        "energy_level": "Focused Analytical Vibe",
        "traits": ["responsible", "dutiful", "logical", "orderly"],
        "description": "You remember tiny factual inconsistencies for years. You trust routines because routines reduce mental chaos. You can become deeply sentimental about traditions. You have a surprisingly dry humor that catches people off guard. You feel responsible for stability even when nobody asked you to.",
        "careers": ["Systems Administrator", "Financial Auditor", "Database Manager", "Operations Manager"],
        "famous_people": ["George Washington", "Angela Merkel", "Queen Elizabeth II", "Warren Buffett"],
        "romantic_compatible": ["Reliable and loyal partners", "People who value traditional romance", "Stable and practical companions"]
    },
    "ISFJ": {
        "title": "The Invisible Protector",
        "color": "#AED6F1",
        "energy_level": "Steady Protective Energy",
        "traits": ["caring", "reliable", "dedicated", "protective"],
        "description": "You solve problems before others even notice them. You can tolerate discomfort for years without complaining. You remember personal details people forget telling you. You feel emotionally safest in familiar environments. Your kindness becomes dangerous when people exploit your loyalty.",
        "careers": ["Healthcare Specialist", "Social worker", "Customer Success Lead", "Office Administrator"],
        "famous_people": ["Mother Teresa", "Beyoncé", "Kate Middleton", "Rosa Parks"],
        "romantic_compatible": ["Warm and appreciative partners", "People who value family and harmony", "Gentle and patient souls"]
    },
    "ESTJ": {
        "title": "The Burden Carrier",
        "color": "#2980B9",
        "energy_level": "Structured Systematic Energy",
        "traits": ["organized", "decisive", "practical", "efficient"],
        "description": "You quietly carry responsibilities other people avoid. You show affection through structure and protection, not words. You can become unexpectedly emotional about family loyalty. You hate inefficiency more than difficulty. Your stress often appears as anger when it is actually exhaustion.",
        "careers": ["Sales Executive", "Project Lead", "Chief Operations Officer", "Financial Manager"],
        "famous_people": ["John D. Rockefeller", "Judge Judy", "Frank Sinatra", "Sonia Sotomayor"],
        "romantic_compatible": ["Partners who respect order and commitment", "People who appreciate acts of service", "Reliable and honest companions"]
    },
    "ESFJ": {
        "title": "The Emotional Historian",
        "color": "#FD79A8",
        "energy_level": "Outgoing Altruistic Vibe",
        "traits": ["outgoing", "supportive", "loyal", "social"],
        "description": "You remember exactly who supported you during difficult periods. You notice subtle social exclusion before others do. You overextend yourself just to maintain harmony. Criticism hurts deeply because you attach self-worth to social value. You secretly wish people cared for you as intensely as you care for them.",
        "careers": ["Human Resources Generalist", "Community Coordinator", "Publicist", "Elementary Teacher"],
        "famous_people": ["Taylor Swift", "Bill Clinton", "Jennifer Lopez", "Steve Harvey"],
        "romantic_compatible": ["Affectionate and expressive partners", "People who love social gatherings", "Loyal and dependable souls"]
    },
    "ISTP": {
        "title": "The Silent Problem Solver",
        "color": "#7F8C8D",
        "energy_level": "Flexible Tactical Energy",
        "traits": ["practical", "bold", "independent", "adaptable"],
        "description": "You emotionally process things while doing physical tasks. You disappear socially when stressed. You dislike being emotionally analyzed. You can become obsessively skilled at niche systems. You value freedom so strongly that control feels suffocating to you.",
        "careers": ["DevOps Engineer", "Forensic Investigator", "Mechanical Engineer", "Systems Technician"],
        "famous_people": ["Michael Jordan", "Clint Eastwood", "Tom Cruise", "Bruce Lee"],
        "romantic_compatible": ["Partners who respect independence", "People who enjoy shared activities over talking", "Spontaneous and low-drama companions"]
    },
    "ISFP": {
        "title": "The Quiet Rebel",
        "color": "#a29bfe",
        "energy_level": "Serene Creative Vibe",
        "traits": ["artistic", "sensitive", "free-spirited", "quiet"],
        "description": "You resist control silently rather than aggressively. You express emotions better through art, music, aesthetics, or actions than words. You disappear when you feel emotionally misunderstood. You have surprisingly strong internal convictions despite appearing relaxed. You value authenticity more than status.",
        "careers": ["Graphic Designer", "Photographer", "Landscape Designer", "Therapist"],
        "famous_people": ["Michael Jackson", "Frida Kahlo", "Lana Del Rey", "Cher"],
        "romantic_compatible": ["Partners who appreciate art and nature", "People who respect emotional boundaries", "Gentle and spontaneous souls"]
    },
    "ESTP": {
        "title": "The Chaos Navigator",
        "color": "#F39C12",
        "energy_level": "Bold Action-Oriented Vibe",
        "traits": ["energetic", "action-oriented", "spontaneous", "bold"],
        "description": "You can enter crisis mode with almost unnatural calmness. You think faster under pressure than during planning. You hate feeling emotionally trapped more than physically trapped. You joke during serious moments to regain control. You learn through impact, not theory.",
        "careers": ["Startup Founder", "Crisis Manager", "Technical Consultant", "Financial Broker"],
        "famous_people": ["Donald Trump", "Madonna", "Ernest Hemingway", "Meryl Streep"],
        "romantic_compatible": ["Fun-loving and active partners", "People who enjoy fast-paced living", "Direct and pragmatic companions"]
    },
    "ESFP": {
        "title": "The Hidden Deep Feeler",
        "color": "#FF7675",
        "energy_level": "Vibrant Playful Spark",
        "traits": ["vivacious", "playful", "spontaneous", "enthusiastic"],
        "description": "You are much more emotionally complex than people assume. You use humor to prevent emotional heaviness. You can become intensely nostalgic. You crave genuine emotional attention, not just popularity. You sense group energy shifts instantly.",
        "careers": ["Event Planner", "Public Speaker", "UX Designer", "Marketing Manager"],
        "famous_people": ["Marilyn Monroe", "Elvis Presley", "Elizabeth Taylor", "Justin Bieber"],
        "romantic_compatible": ["Partners who love to laugh and have fun", "People who are affectionate and present", "Spontaneous and outgoing companions"]
    }
}


def analyze_photo_vibe(image_bytes: bytes) -> dict[str, Any]:
    """Analyze the visual aura properties of a captured selfie.
    
    Using standard Pillow (PIL) math, this:
    1. Measures luminance/brightness of the pixels (0-255).
    2. Calculates warm vs. cool color balance (ratio of R/B channels).
    3. Calculates visual complexity/variance (standard deviation of grayscale).
    
    Args:
        image_bytes: The raw photo image bytes.
        
    Returns:
        A dictionary containing visual vibe stats:
        {
            "brightness": float (0-100),
            "warmth": float (-50 to 50, positive=warm, negative=cool),
            "complexity": float (0-100),
            "visual_aura": str (e.g. 'Warm Sunset', 'Deep Ocean'),
            "visual_color": str
        }
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # Downsample for fast pixel calculation
        img = img.resize((150, 150))
        
        # Calculate stats
        stat = ImageStat.Stat(img)
        
        # 1. Brightness (using standard RGB weights)
        if len(stat.mean) >= 3:
            r_mean, g_mean, b_mean = stat.mean[:3]
            luminance = (0.299 * r_mean) + (0.587 * g_mean) + (0.114 * b_mean)
        else:
            luminance = stat.mean[0] if stat.mean else 127
        
        brightness_pct = max(0.0, min(100.0, (luminance / 255.0) * 100.0))
        
        # 2. Warmth (Red vs Blue balance)
        if len(stat.mean) >= 3:
            r_val, _, b_val = stat.mean[:3]
            warmth = r_val - b_val  # Positive means warm/reddish, negative means cool/bluish
        else:
            warmth = 0
            
        warmth_score = max(-50.0, min(50.0, warmth))
        
        # 3. Complexity/Variance (Standard deviation on grayscale version)
        gray_img = img.convert("L")
        gray_stat = ImageStat.Stat(gray_img)
        std_dev = gray_stat.stddev[0] if gray_stat.stddev else 40
        complexity_pct = max(0.0, min(100.0, (std_dev / 128.0) * 100.0))
        
        # 4. Resolve Visual Vibe Description & Color
        if brightness_pct > 65:
            if warmth_score > 5:
                vibe_desc = "Radiant Golden Aura"
                vibe_color = "#F1C40F"
            else:
                vibe_desc = "Celestial Astral Aura"
                vibe_color = "#00BCD4"
        elif brightness_pct < 35:
            if warmth_score > 5:
                vibe_desc = "Deep Forest Aura"
                vibe_color = "#27AE60"
            else:
                vibe_desc = "Cosmic Mystic Aura"
                vibe_color = "#9B59B6"
        else:
            if warmth_score > 10:
                vibe_desc = "Sunset Amber Aura"
                vibe_color = "#E67E22"
            elif warmth_score < -10:
                vibe_desc = "Ocean Breeze Aura"
                vibe_color = "#3498DB"
            else:
                vibe_desc = "Balanced Jade Aura"
                vibe_color = "#1ABC9C"
                
        return {
            "brightness": round(brightness_pct, 2),
            "warmth": round(warmth_score, 2),
            "complexity": round(complexity_pct, 2),
            "visual_aura": vibe_desc,
            "visual_color": vibe_color
        }
        
    except Exception as exc:
        logger.error("Failed to analyze photo vibe: %s. Using neutral defaults.", exc)
        return {
            "brightness": 50.0,
            "warmth": 0.0,
            "complexity": 50.0,
            "visual_aura": "Balanced Jade Aura",
            "visual_color": "#1ABC9C"
        }


def analyze_mbti(answers: dict[str, int], image_bytes: Optional[bytes] = None) -> dict[str, Any]:
    """Calculate personality MBTI profile based on 20 questions + optional camera photo.
    
    1. Maps answers (1-5 scale) to (-2 to +2).
    2. Sums dichotomy values.
    3. Incorporates visual vibe parameters (brightness/warmth/variance) to shift weights:
       - Bright, warm photo -> leans toward E and F.
       - Deep, cool photo -> leans toward I and T.
       - High pixel complexity/entropy -> leans toward P (boosting spontaneous adaptability).
    4. Calculates percentages and maps to 16 personality profiles.
    
    Args:
        answers: A dictionary mapping question IDs ("q1" to "q20") to answers (1 to 5).
        image_bytes: Optional raw photo bytes.
        
    Returns:
        A structured profile dictionary.
    """
    # 1. Process visual properties first if available
    vibe = {
        "brightness": 50.0,
        "warmth": 0.0,
        "complexity": 50.0,
        "visual_aura": "Balanced Jade Aura",
        "visual_color": "#1ABC9C"
    }
    if image_bytes:
        vibe = analyze_photo_vibe(image_bytes)

    # 2. Accumulate scores per dichotomy
    scores = {"EI": 0.0, "SN": 0.0, "TF": 0.0, "JP": 0.0}
    counts = {"EI": 0, "SN": 0, "TF": 0, "JP": 0}
    
    for q in MBTI_QUESTIONS:
        q_id = q["id"]
        dim = q["dimension"]
        direction = q["direction"]
        
        if q_id in answers:
            ans_val = float(answers[q_id])
            # Map 1-5 to -2 to +2
            mapped = ans_val - 3.0
            scores[dim] += mapped * direction
            counts[dim] += 1

    # Normalize baseline to average scale (range -2.0 to +2.0)
    for dim in scores:
        if counts[dim] > 0:
            scores[dim] = scores[dim] / counts[dim]

    # 3. Dynamic Visual Vibe Shifts
    # Brightness (0 to 100) -> Shifts toward E (high brightness) or I (deep contrast)
    brightness_shift = (vibe["brightness"] - 50.0) / 100.0  # Range -0.5 to +0.5
    scores["EI"] += brightness_shift * 0.4
    
    # Warmth (-50 to 50) -> Shifts toward F (warm feelings) or T (cool logic)
    # Note: TF dichotomy: + is Thinking, - is Feeling. Warmth > 0 decreases TF (shifts to Feeling)
    warmth_shift = vibe["warmth"] / 50.0  # Range -1.0 to +1.0
    scores["TF"] -= warmth_shift * 0.5
    
    # Complexity (0 to 100) -> Shifts toward P (Perceiving) vs J (Judging)
    # Note: JP dichotomy: + is Judging, - is Perceiving. High complexity shifts to Perceiving (-)
    complexity_shift = (vibe["complexity"] - 50.0) / 100.0  # Range -0.5 to +0.5
    scores["JP"] -= complexity_shift * 0.4

    # 4. Clamp scores to standard range [-2.0, 2.0]
    for dim in scores:
        scores[dim] = max(-2.0, min(2.0, scores[dim]))

    # 5. Translate to letter codes and percentages (0-100%)
    # EI: + leans E, - leans I
    e_pct = int(round(((scores["EI"] + 2.0) / 4.0) * 100))
    i_pct = 100 - e_pct
    letter_ei = "E" if scores["EI"] >= 0 else "I"
    
    # SN: + leans S, - leans N
    s_pct = int(round(((scores["SN"] + 2.0) / 4.0) * 100))
    n_pct = 100 - s_pct
    letter_sn = "S" if scores["SN"] >= 0 else "N"
    
    # TF: + leans T, - leans F
    t_pct = int(round(((scores["TF"] + 2.0) / 4.0) * 100))
    f_pct = 100 - t_pct
    letter_tf = "T" if scores["TF"] >= 0 else "F"
    
    # JP: + leans J, - leans P
    j_pct = int(round(((scores["JP"] + 2.0) / 4.0) * 100))
    p_pct = 100 - j_pct
    letter_jp = "J" if scores["JP"] >= 0 else "P"

    # Assemble MBTI Code
    mbti_type = f"{letter_ei}{letter_sn}{letter_tf}{letter_jp}"
    profile = MBTI_PROFILES.get(mbti_type, MBTI_PROFILES["INFJ"])

    # 6. Energy and confidence scores
    # Energy: influenced by visual complexity + warmth
    base_energy = 50.0 + (vibe["complexity"] * 0.3) + (abs(vibe["warmth"]) * 0.4)
    energy_score = max(0, min(100, int(round(base_energy))))
    
    # Confidence: how extreme are the personality leanings + length
    pct_extremes = [abs(e_pct - 50), abs(s_pct - 50), abs(t_pct - 50), abs(j_pct - 50)]
    avg_leaning = sum(pct_extremes) / len(pct_extremes)  # Max 50
    confidence = 40.0 + (avg_leaning * 1.2)
    confidence_score = max(0, min(100, int(round(confidence))))

    return {
        "mbti_type": mbti_type,
        "title": profile["title"],
        "aura_color": profile["color"],
        "energy_level": profile["energy_level"],
        "traits": profile["traits"],
        "description": profile["description"],
        "careers": profile["careers"],
        "famous_people": profile["famous_people"],
        "romantic_compatible": profile.get("romantic_compatible", []),
        "energy_score": energy_score,
        "confidence_score": confidence_score,
        "dichotomies": {
            "E": e_pct,
            "I": i_pct,
            "S": s_pct,
            "N": n_pct,
            "T": t_pct,
            "F": f_pct,
            "J": j_pct,
            "P": p_pct
        },
        "vibe": vibe,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

