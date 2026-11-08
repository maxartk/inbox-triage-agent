"""CLI for triage, listing, approval and audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .classifier import classify
from .drafts import draft_reply
from .outbox import Outbox


def cmd_triage(args) -> int:
    source = Path(args.input)
    if not source.exists():
        print(f"Vstup nenalezen: {source}", file=sys.stderr)
        return 1

    outbox = Outbox(Path(args.outbox))
    queued = escalated = 0
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        message = json.loads(line)
        triage = classify(message.get("subject", ""), message.get("body", ""))

        item = {
            "id": message["id"],
            "from": message.get("from", ""),
            "subject": message.get("subject", ""),
            "triage": triage.as_dict(),
        }

        if triage.needs_human:
            item["draft"] = None
            item["status"] = "needs_human"
            escalated += 1
        else:
            item["draft"] = draft_reply(triage.intent, triage.order_id, triage.language)
            queued += 1

        outbox.submit(item)
        print(f"[{item['status']:12}] {item['id']:10} {triage.intent:13} skóre={triage.score:.2f} obj={triage.order_id or '-'}")

    print(f"\nZařazeno k schválení: {queued} | eskalováno na člověka: {escalated}")
    return 0


def cmd_list(args) -> int:
    outbox = Outbox(Path(args.outbox))
    items = outbox.list_pending()
    if not items:
        print("Fronta je prázdná.")
        return 0
    for item in items:
        triage = item.get("triage", {})
        print(f"{item['id']:10} {item.get('status', ''):16} {triage.get('intent', ''):13} obj={triage.get('order_id') or '-'}")
    print(f"\nCelkem: {len(items)}")
    return 0


def cmd_approve(args) -> int:
    outbox = Outbox(Path(args.outbox))
    result = outbox.approve(args.id, args.by)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_reject(args) -> int:
    outbox = Outbox(Path(args.outbox))
    result = outbox.reject(args.id, args.by, args.reason or "")
    print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_audit(args) -> int:
    outbox = Outbox(Path(args.outbox))
    for record in outbox.read_audit():
        print(f"{record['ts']} {record['action']:30} {record['id']:10} {record['actor']}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="inbox-triage", description="Triage zákaznických e-mailů s lidským schválením")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("triage", help="Roztřídit JSONL inbox")
    p.add_argument("--in", dest="input", required=True)
    p.add_argument("--outbox", default="outbox")
    p.set_defaults(func=cmd_triage)

    p = sub.add_parser("list", help="Co čeká na schválení")
    p.add_argument("--outbox", default="outbox")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("approve", help="Schválit návrh")
    p.add_argument("--outbox", default="outbox")
    p.add_argument("--id", required=True)
    p.add_argument("--by", required=True, help="Jméno schvalovatele (audit)")
    p.set_defaults(func=cmd_approve)

    p = sub.add_parser("reject", help="Zamítnout návrh")
    p.add_argument("--outbox", default="outbox")
    p.add_argument("--id", required=True)
    p.add_argument("--by", required=True)
    p.add_argument("--reason", default="")
    p.set_defaults(func=cmd_reject)

    p = sub.add_parser("audit", help="Výpis auditu")
    p.add_argument("--outbox", default="outbox")
    p.set_defaults(func=cmd_audit)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
