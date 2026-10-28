"""JSON-schema helpers. No third-party imports, so it is easy to test."""


def inline_refs(schema: dict) -> dict:
    """Make a pydantic JSON schema simple enough for every model:
    resolve $ref/$defs, turn `anyOf: [X, null]` into X, drop `default`."""
    defs = schema.get("$defs", {})

    def walk(node):
        if isinstance(node, list):
            return [walk(v) for v in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            return walk(defs[node["$ref"].rsplit("/", 1)[-1]])
        options = node.get("anyOf")
        if options:
            non_null = [o for o in options if o.get("type") != "null"]
            if len(non_null) == 1:
                rest = {k: v for k, v in node.items() if k != "anyOf"}
                return walk({**non_null[0], **rest})
        out = {}
        for key, value in node.items():
            if key in ("$defs", "default"):
                continue
            if key == "properties":  # keys here are field names, not schema keywords
                out[key] = {name: walk(sub) for name, sub in value.items()}
            else:
                out[key] = walk(value)
        return out

    return walk(schema)
