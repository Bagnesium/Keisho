"""Unauthenticated metadata only, through the runner's verified urllib opener."""

import hashlib
import json
from pathlib import Path
import ssl
import sys
from urllib import request

from keisho.agents.providers.openai_chat import verified_opener
from keisho.agents.providers.openrouter_chat import BASE_URL, MODEL_ALIASES, validate_catalog
from keisho.core import canonical_json, digest, utc_now
from keisho.pilot.tasks import REPO

ca_file = REPO / ".cache/certificates/openrouter-ca-v1.2.0.pem"
opener = verified_opener(ca_file)


def public_get(path):
    message = request.Request(BASE_URL + path, headers={"Accept": "application/json"}, method="GET")
    assert message.get_header("Authorization") is None
    with opener.open(message, timeout=30) as response:
        return json.loads(response.read())


models = public_get("/models")
selected = [row for row in models["data"] if row["id"] in MODEL_ALIASES.values()]
assert len(selected) == 2
catalog = {"version": "1.2.0", "checked_at": utc_now(), "source": BASE_URL + "/models",
           "authentication_attached": False, "models": selected,
           "endpoints": {alias: public_get("/models/" + alias + "/endpoints") for alias in MODEL_ALIASES.values()}}
validate_catalog(catalog)
with (REPO / "analysis/openrouter-catalog-v1.2.0.json").open("x") as stream:
    stream.write(canonical_json(catalog) + "\n")
context = ssl.create_default_context(cafile=str(ca_file))
record = {"version": "1.2.0", "checked_at": utc_now(), "python_executable": sys.executable,
          "python_version": sys.version.split()[0], "http_client": "urllib.request; shared verified_opener/NoRedirect",
          "initial_default_tls_failure": {"reason": "SSLCertVerificationError", "verify_code": 20,
                                          "missing_default_ca_file": ssl.get_default_verify_paths().openssl_cafile},
          "repair": "explicit project-local copy of the already installed certifi bundle; no system changes",
          "ca_file": str(ca_file), "ca_sha256": hashlib.sha256(ca_file.read_bytes()).hexdigest(),
          "certificate_verification": context.verify_mode == ssl.CERT_REQUIRED,
          "hostname_verification": context.check_hostname, "public_verified_https": True,
          "authenticated_metadata_calls": 0, "inference_calls": 0, "catalog_sha256": digest(catalog),
          "model_mapping": {canonical: [alias, canonical] for canonical, alias in MODEL_ALIASES.items()}}
with (REPO / "analysis/openrouter-connection-v1.2.0.json").open("x") as stream:
    stream.write(canonical_json(record) + "\n")
print(json.dumps({"public_verified_https": True, "credentials_attached": False,
                  "catalog_sha256": digest(catalog), "model_mapping": record["model_mapping"]}))
