# inbox-triage-agent

Roztřídí zákaznické e-maily e-shopu, vytáhne číslo objednávky a připraví návrh
odpovědi — ale **nic neodešle samo**. Každý návrh jde do fronty `pending_approval`
a čeká na potvrzení člověkem; až potom se přesune do `sent` a zapíše se do auditu.

Navrženo pro reálný provoz: lidské schválení je součást workflow, ne obcházená
překážka. Historie rozhodnutí zůstává (kdo, kdy, co schválil).

## Proč

V diskusích o automatizaci e-shopů se opakuje totéž: automatizovat se vyplatí
opakované dotazy („kdy dorazí objednávka", „jak vrátit zboží"), ale plně
automatické odesílání odpovědí zákazníkům je risk — jedna špatná šablona a
zákazník dostane nepravdivou informaci. Proto: **agent připraví, člověk potvrdí.**

## Použití

```bash
# 1) roztřídit inbox (JSONL: {"id","from","subject","body"})
python -m inbox_triage triage --in examples/messages.jsonl --outbox outbox

# 2) co čeká na schválení
python -m inbox_triage list --outbox outbox

# 3) schválit / zamítnout (--by = kdo rozhodl, jde do auditu)
python -m inbox_triage approve --outbox outbox --id MSG-001 --by maksym
python -m inbox_triage reject  --outbox outbox --id MSG-002 --by maksym --reason "chybí číslo objednávky"

# 4) audit
python -m inbox_triage audit --outbox outbox
```

## Jak rozhoduje

| Krok | Co dělá |
|---|---|
| extrakce | číslo objednávky (`#12345`, `obj. č. 12345`, `order 12345`) |
| klasifikace | `return`, `claim`, `order_status`, `invoice`, `address_change`, `other` |
| skóre | váha klíčových slov + přítomnost čísla objednávky + jazyk |
| eskalace | `other`, nebo skóre < 0.55 → `needs_human`, bez návrhu odpovědi |
| návrh | česká šablona podle záměru, s místem pro číslo objednávky |
| gate | `pending_approval` → `approved` → `sent`, každý přechod v `audit.jsonl` |

Klasifikátor je záměrně **deterministický a čitelný** — u zákaznické komunikace
je důležitější vysvětlitelné rozhodnutí než „chytrý" model. Rozhraní je
připravené na výměnu za LLM (`classifier.py` má jednu funkci `classify`).

## Bezpečnostní pravidla

- žádné SMTP, žádné odesílání — jen soubory a audit;
- `approve` vyžaduje `--by` (jméno schvalovatele), jinak odmítne;
- druhý `approve` stejného ID nic nepřepíše (idempotence, v audit jen pokus);
- text se nikdy neodesílá, pokud záměr = `other` nebo chybí číslo objednávky
  u `order_status`.

## Testy

```bash
python -m unittest discover -s tests -v
```

MIT licencováno.

## Poznámka ke vzniku

Téma vychází z diskusí o tom, které zákaznické dotazy má smysl automatizovat a proč
plně automatické odesílání odpovědí nedoporučují. Kód je vlastní implementace.
