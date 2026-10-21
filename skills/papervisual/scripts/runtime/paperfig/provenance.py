"""Source presence is distinct from author confirmation and scientific validity."""

import json


SOURCE_FIELDS = {"pages", "section", "theorem", "equation", "explanation"}


def source_present(value):
    if isinstance(value, str):
        return bool(value.strip())
    return (isinstance(value, dict) and bool(value)
            and not value.keys() - SOURCE_FIELDS
            and all(isinstance(v, str) for v in value.values())
            and any(value.get(k, "").strip() for k in SOURCE_FIELDS - {"explanation"}))


def source_text(value):
    return value if isinstance(value, str) else json.dumps(value or {}, ensure_ascii=False)


def status(item):
    return item.get("review_status", "needs_review")


def source_findings(brief):
    items = [("Central claim", brief.get("claim_source"))]
    items += [(f"Node '{n['id']}'", n.get("source")) for n in brief["nodes"]]
    items += [(f"Edge {i} ({e['from']} -> {e['to']})", e.get("source"))
              for i, e in enumerate(brief["edges"])]
    return [f"{label} has no source anchor." for label, value in items if not source_present(value)]
