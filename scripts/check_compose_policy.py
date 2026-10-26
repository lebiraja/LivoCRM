"""Compose security policy check (SEC-01). Stdlib only; needs the docker CLI.

Asserts:
  - only nginx publishes a port by default; db never does
  - every default service has a healthcheck; db gets no env_file
  - dev-profile ports bind to 127.0.0.1
  - password/secret-like environment values are ${VAR} references, never literals
  - every image tag is explicit and not `latest`

Usage: python3 scripts/check_compose_policy.py   (exit 1 on any violation)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SECRET_KEY = re.compile(r"PASSWORD|SECRET|TOKEN|_KEY$", re.IGNORECASE)
ENV_REF = re.compile(r"^\$\{[A-Z0-9_]+(:?[-?][^}]*)?\}$")
PINNED = re.compile(r"^[^:]+:(?!latest$)\d+\.\d+[\w.-]*$")


def compose_config(*profiles: str, interpolate: bool = True) -> dict[str, Any]:
    flags = [arg for p in profiles for arg in ("--profile", p)]
    out = subprocess.run(
        ["docker", "compose", *flags, "config", "--format", "json", *([] if interpolate else ["--no-interpolate"])],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    return json.loads(out.stdout)


def violations() -> list[str]:
    errors: list[str] = []

    default = compose_config()["services"]
    for name, svc in default.items():
        if svc.get("ports") and name != "nginx":
            errors.append(f"{name}: publishes a host port in the default profile")
        if "healthcheck" not in svc:
            errors.append(f"{name}: has no healthcheck")
    if "env_file" in default["db"]:
        errors.append("db: env_file would hand every app secret to the database container")

    dev = compose_config("dev")["services"]
    for name, svc in dev.items():
        for port in svc.get("ports", []):
            if name != "nginx" and port.get("host_ip") != "127.0.0.1":
                errors.append(f"{name}: port {port.get('published')} is not bound to 127.0.0.1")

    raw = compose_config("dev", "test", interpolate=False)["services"]
    for name, svc in raw.items():
        for key, value in (svc.get("environment") or {}).items():
            if SECRET_KEY.search(key) and value is not None and not ENV_REF.match(str(value)):
                errors.append(f"{name}: {key} is a literal, use ${{VAR}} from .env")
        image = svc.get("image")
        if image and not PINNED.match(image):
            errors.append(f"{name}: image {image} is not pinned to a version")

    return errors


if __name__ == "__main__":
    found = violations()
    for line in found:
        print(f"FAIL {line}")
    print("compose policy: ok" if not found else f"compose policy: {len(found)} violation(s)")
    sys.exit(1 if found else 0)
