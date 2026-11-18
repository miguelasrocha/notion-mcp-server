#!/usr/bin/env python3
"""Splice the Life OS view/database/comment operations into the bundled spec.

The upstream spec lags the public Notion OpenAPI (views and database creation
are absent). This adds only the operations Hermes needs, copying any referenced
components from the public spec, and pins Notion-Version to 2026-03-11.
"""
import argparse
import json
import sys

VIEW_PATHS = [
    "/v1/views",
    "/v1/views/{view_id}",
    "/v1/views/{view_id}/queries",
    "/v1/views/{view_id}/queries/{query_id}",
]
COPY_PATHS = ["/v1/comments/{comment_id}"]


def refs(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str) and value.startswith("#/components/"):
                yield value
            else:
                yield from refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from refs(item)


def collect_components(root, nodes):
    pending = []
    for node in nodes:
        pending.extend(refs(node))
    copied = {}
    while pending:
        ref = pending.pop()
        _, _, kind, name = ref.split("/", 3)
        if kind == "parameters" and name == "notionVersion":
            continue
        existing = root["components"].get(kind, {}).get(name)
        if existing is not None:
            continue
        source = full["components"][kind][name]
        copied.setdefault(kind, {})[name] = source
        pending.extend(refs(source))
    return copied


ap = argparse.ArgumentParser()
ap.add_argument("--source", required=True)
ap.add_argument("--target", required=True)
args = ap.parse_args()
full = json.load(open(args.source))
spec = json.load(open(args.target))
added = []

for path in VIEW_PATHS:
    spec["paths"][path] = full["paths"][path]
    added.append(spec["paths"][path])

spec["paths"]["/v1/databases"] = {"post": full["paths"]["/v1/databases"]["post"]}
added.append(spec["paths"]["/v1/databases"]["post"])

patch_db = full["paths"]["/v1/databases/{database_id}"]["patch"]
patch_db["operationId"] = "update-a-database"
spec["paths"]["/v1/databases/{database_id}"]["patch"] = patch_db
added.append(patch_db)

list_comments = full["paths"]["/v1/comments"]["get"]
list_comments["operationId"] = "list-comments"
spec["paths"]["/v1/comments"]["get"] = list_comments
added.append(list_comments)

comment = full["paths"]["/v1/comments/{comment_id}"]
comment["get"]["operationId"] = "retrieve-comment-by-id"
spec["paths"].update({p: full["paths"][p] for p in COPY_PATHS})
added.extend(comment.values())

spec["components"]["parameters"]["notionVersion"]["schema"] = {
    "type": "string",
    "default": "2026-03-11",
}

for kind, items in collect_components(spec, added).items():
    spec["components"].setdefault(kind, {}).update(items)

json.dump(spec, open(args.target, "w"), indent=2)
print(f"paths={len(spec['paths'])} added_ops={sum(len(v) for v in added if isinstance(v, dict))}")
