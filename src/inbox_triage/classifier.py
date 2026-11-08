"""Deterministic, explainable triage of customer e-mails."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

ORDER_PATTERNS = (
    re.compile(r"(?:#|obj\.?\s*(?:č\.?)?|objedn[áa]vk[ay uí]*\s*(?:č\.?)?)\s*(\d{4,})", re.I),
    re.compile(r"\border\s*(?:no\.?|number|#)?\s*(\d{4,})", re.I),
)

INTENT_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "return": (
        "vr[áa]cen", "vr[áa]tit", "vratk", "odstoup", "14 dn", "return", "refund",
        "поверн", "верну", "повернут",
    ),
    "claim": (
        "reklamac", "reklam", "z[áa]vad", "po[šs]koz", "nefunk", "praskl", "chyb[íi]", "skol",
        "claim", "defect", "broken", "брак", "не працю", "скол", "пошкодж",
    ),
    "order_status": (
        "kde je", "kdy doraz", "doru[čc]en", "stav objedn[áa]vky", "sledov[áa]n",
        "tracking", "where is", "delivery", "доставк", "де замовлен",
    ),
    "invoice": (
        "faktur", "da[ňn]ov[ýy] doklad", "invoice", "účet", "dph", "рахунок",
    ),
    "address_change": (
        "zm[ěe]na adres", "p[řr]eadres", "jin[áa] adres", "change address",
        "змін", "адрес",
    ),
}

URGENT_HINTS = ("urgent", "ihned", "dnes", "asap", "spěchá", "терміново", "сьогодні")

LANG_HINTS = {
    "cs": ("objednávk", "prosím", "dobrý den", "zboží", "děkuji"),
    "uk": ("замовлен", "будь ласка", "дякую", "товар", "вітаю"),
    "en": ("order", "hello", "please", "thanks", "delivery"),
}


@dataclass
class Triage:
    intent: str
    score: float
    order_id: str = ""
    language: str = "cs"
    urgent: bool = False
    needs_human: bool = False
    reasons: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        return {
            "intent": self.intent,
            "score": round(self.score, 3),
            "order_id": self.order_id,
            "language": self.language,
            "urgent": self.urgent,
            "needs_human": self.needs_human,
            "reasons": self.reasons,
        }


def extract_order_id(text: str) -> str:
    for pattern in ORDER_PATTERNS:
        match = pattern.search(text or "")
        if match:
            return match.group(1)
    return ""


def detect_language(text: str) -> str:
    low = (text or "").lower()
    best, best_hits = "cs", 0
    for language, hints in LANG_HINTS.items():
        hits = sum(1 for hint in hints if hint in low)
        if hits > best_hits:
            best, best_hits = language, hits
    return best


def classify(subject: str, body: str, threshold: float = 0.55) -> Triage:
    """Score every intent by keyword hits; return the strongest one."""
    text = f"{subject} {body}".lower()
    order_id = extract_order_id(f"{subject} {body}")
    language = detect_language(text)
    urgent = any(hint in text for hint in URGENT_HINTS)

    scores: Dict[str, float] = {}
    hits_by_intent: Dict[str, List[str]] = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        hits = [kw for kw in keywords if re.search(kw, text)]
        if hits:
            scores[intent] = min(1.0, 0.35 + 0.2 * len(hits))
            hits_by_intent[intent] = hits

    if not scores:
        return Triage(
            intent="other",
            score=0.0,
            order_id=order_id,
            language=language,
            urgent=urgent,
            needs_human=True,
            reasons=["žádné klíčové slovo zákaznických záměrů"],
        )

    intent = max(scores, key=lambda k: scores[k])
    score = scores[intent]
    reasons = [f"klíčová slova: {', '.join(hits_by_intent[intent])}"]

    if order_id:
        score = min(1.0, score + 0.1)
        reasons.append(f"nalezeno číslo objednávky {order_id}")
    else:
        reasons.append("číslo objednávky nenalezeno")

    needs_human = score < threshold or (intent == "order_status" and not order_id)
    if needs_human:
        reasons.append("nízká jistota nebo chybějící číslo objednávky → člověk")

    return Triage(
        intent=intent,
        score=score,
        order_id=order_id,
        language=language,
        urgent=urgent,
        needs_human=needs_human,
        reasons=reasons,
    )
