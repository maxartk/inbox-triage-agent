"""Czech reply templates, one per intent. No promises we cannot keep."""

from __future__ import annotations

from typing import Dict

SIGNATURE = "\n\nS pozdravem\nZákaznická podpora"

TEMPLATES: Dict[str, str] = {
    "return": (
        "Dobrý den,\n\n"
        "děkujeme za zprávu. Vrácení zboží je možné do 14 dnů od převzetí bez udání důvodu.\n"
        "Objednávka: {order}\n\n"
        "Stačí, když nám napíšete, zda chcete zboží poslat zpět přepravcem, nebo vrátit na prodejně. "
        "Penize vracíme na účet, ze kterého byla objednávka zaplacena, do 14 dnů od vrácení."
    ),
    "claim": (
        "Dobrý den,\n\n"
        "mrzí nás, že zboží neodpovídá očekávání. Reklamaci jsme přijali k posouzení.\n"
        "Objednávka: {order}\n\n"
        "Prosíme o 2–3 fotografie závady a krátký popis, co přesně nefunguje. "
        "Jakmile je budeme mít, ozveme se s dalším postupem (oprava, výměna, nebo vrácení peněz)."
    ),
    "order_status": (
        "Dobrý den,\n\n"
        "děkujeme za objednávku. Stav zásilky jsme ověřili.\n"
        "Objednávka: {order}\n\n"
        "Jakmile zásilka opustí sklad, dostanete e-mailem číslo pro sledování. "
        "Pokud do 48 hodin nepřijde, napište nám prosím znovu."
    ),
    "invoice": (
        "Dobrý den,\n\n"
        "fakturu jsme znovu odeslali na e-mail uvedený v objednávce.\n"
        "Objednávka: {order}\n\n"
        "Pokud ji stále nevidíte, zkontrolujte prosím složku spam nebo nám potvrďte jinou e-mailovou adresu."
    ),
    "address_change": (
        "Dobrý den,\n\n"
        "změnu doručovací adresy lze provést do chvíle, než zásilku předáme přepravci.\n"
        "Objednávka: {order}\n\n"
        "Napište nám prosím novou adresu a my ověříme, zda ji ještě stíháme změnit. "
        "Pokud už je zásilka na cestě, doporučíme přesměrování u přepravce."
    ),
}


def draft_reply(intent: str, order_id: str, language: str = "cs") -> Dict[str, str]:
    """Return subject + body draft for the given intent."""
    if intent not in TEMPLATES:
        raise ValueError(f"Pro záměr '{intent}' nemáme šablonu")

    order = order_id or "(neuvedeno)"
    prefix = ""
    if language == "uk":
        prefix = "Dobrý den, / Вітаю,\n\n"
    elif language == "en":
        prefix = "Hello,\n\n"

    body = TEMPLATES[intent].format(order=order)
    subject_map = {
        "return": "Vrácení zboží – objednávka {order}",
        "claim": "Reklamace – objednávka {order}",
        "order_status": "Stav objednávky {order}",
        "invoice": "Faktura – objednávka {order}",
        "address_change": "Změna adresy – objednávka {order}",
    }
    return {
        "subject": subject_map[intent].format(order=order),
        "body": prefix + body + SIGNATURE,
    }
