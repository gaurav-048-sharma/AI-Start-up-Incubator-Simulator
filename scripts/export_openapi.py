#!/usr/bin/env python3
"""
OpenAPI spec export + TypeScript SDK generation script.
Generates the OpenAPI JSON spec from FastAPI and optionally creates
type-safe TypeScript types for the frontend.

Usage:
    python scripts/export_openapi.py           # Export OpenAPI JSON
    python scripts/export_openapi.py --types    # Also generate TS types
"""

import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "true")


def export_openapi():
    """Export the OpenAPI spec from the FastAPI app."""
    from app.main import app

    spec = app.openapi()
    spec_path = os.path.join(os.path.dirname(__file__), "..", "infra", "openapi.json")
    os.makedirs(os.path.dirname(spec_path), exist_ok=True)

    with open(spec_path, "w") as f:
        json.dump(spec, f, indent=2, default=str)

    print(f"✅ OpenAPI spec exported to: {spec_path}")
    print(f"   Endpoints: {len(spec.get('paths', {}))}")
    print(f"   Schemas: {len(spec.get('components', {}).get('schemas', {}))}")
    return spec


def generate_typescript_types(spec: dict):
    """Generate TypeScript type definitions from OpenAPI schemas."""
    schemas = spec.get("components", {}).get("schemas", {})
    lines = [
        "// Auto-generated from OpenAPI spec — do not edit manually",
        f"// Generated at: {__import__('datetime').datetime.utcnow().isoformat()}Z",
        "",
    ]

    type_map = {
        "string": "string",
        "integer": "number",
        "number": "number",
        "boolean": "boolean",
        "object": "Record<string, any>",
        "array": "any[]",
    }

    for name, schema in schemas.items():
        if schema.get("enum"):
            values = " | ".join(f'"{v}"' for v in schema["enum"])
            lines.append(f"export type {name} = {values};")
            lines.append("")
            continue

        props = schema.get("properties", {})
        required = set(schema.get("required", []))

        lines.append(f"export interface {name} {{")
        for prop_name, prop_def in props.items():
            ts_type = type_map.get(prop_def.get("type", "any"), "any")

            if prop_def.get("anyOf"):
                types = []
                for t in prop_def["anyOf"]:
                    if "$ref" in t:
                        ref_name = t["$ref"].split("/")[-1]
                        types.append(ref_name)
                    elif t.get("type"):
                        types.append(type_map.get(t["type"], "any"))
                ts_type = " | ".join(types) if types else "any"
            elif "$ref" in prop_def:
                ts_type = prop_def["$ref"].split("/")[-1]
            elif prop_def.get("type") == "array":
                item_type = "any"
                items = prop_def.get("items", {})
                if "$ref" in items:
                    item_type = items["$ref"].split("/")[-1]
                elif items.get("type"):
                    item_type = type_map.get(items["type"], "any")
                ts_type = f"{item_type}[]"

            optional = "?" if prop_name not in required else ""
            lines.append(f"  {prop_name}{optional}: {ts_type};")

        lines.append("}")
        lines.append("")

    types_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "lib", "api-types.generated.ts")
    with open(types_path, "w") as f:
        f.write("\n".join(lines))

    print(f"✅ TypeScript types generated: {types_path}")
    print(f"   Types: {len(schemas)}")


if __name__ == "__main__":
    spec = export_openapi()
    if "--types" in sys.argv:
        generate_typescript_types(spec)
