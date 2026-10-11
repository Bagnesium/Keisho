"""Read-only byte attribution of the unchanged, complete fixed JSON baseline."""

from collections import Counter
from fractions import Fraction
import json

from keisho.compiler.fixed import compile_fixed
from keisho.core import canonical_json, require, text_digest
from keisho.logging.raw import RawRun
from .state_builder import build_state
from .tasks import REPO
from .tokenizer import NativeTokenizer

CATEGORIES = ("substantive_statements", "evidence_excerpts", "duplicated_content",
              "identifiers_and_metadata", "serialization_overhead")
CONTENT_FIELDS = {"description", "statement", "reason", "failure", "attempt", "change",
                  "retry_conditions", "question", "answer", "result", "excerpt"}


def attribute(text, counter):
    """Split token weight by labelled UTF-8 bytes, so categories are additive."""
    pieces, labels, seen, duplicates = [], [], {}, []

    def append(fragment, category):
        data = fragment.encode()
        pieces.append(data)
        labels.extend([category] * len(data))

    def string(value, category):
        encoded = canonical_json(value)
        append('"', "serialization_overhead")
        index = 1
        while index < len(encoded) - 1:
            if encoded[index] == "\\":
                append("\\", "serialization_overhead")
                index += 1
                # Literal JSON escape marker/hex syntax is overhead. A short
                # escaped quote/backslash/newline contributes its second byte.
                if encoded[index] == "u":
                    append(encoded[index:index + 5], "serialization_overhead")
                    index += 5
                    continue
            append(encoded[index], category)
            index += 1
        append('"', "serialization_overhead")

    def walk(value, path=()):
        if isinstance(value, dict):
            append("{", "serialization_overhead")
            for index, key in enumerate(sorted(value)):
                if index:
                    append(",", "serialization_overhead")
                string(key, "serialization_overhead")
                append(":", "serialization_overhead")
                walk(value[key], path + (key,))
            append("}", "serialization_overhead")
        elif isinstance(value, list):
            append("[", "serialization_overhead")
            for index, item in enumerate(value):
                if index:
                    append(",", "serialization_overhead")
                walk(item, path + (index,))
            append("]", "serialization_overhead")
        elif isinstance(value, str):
            field = next((part for part in reversed(path) if isinstance(part, str)), "")
            category = "identifiers_and_metadata"
            if field in CONTENT_FIELDS:
                category = "evidence_excerpts" if field in ("excerpt", "result") else "substantive_statements"
                if value in seen:
                    category = "duplicated_content"
                    duplicates.append({"path": list(path), "first_path": list(seen[value]), "sha256": text_digest(value), "utf8_bytes": len(value.encode())})
                else:
                    seen[value] = path
            string(value, category)
        else:
            append(canonical_json(value), "identifiers_and_metadata")

    walk(json.loads(text))
    require(b"".join(pieces) == text.encode(), "audit must reproduce original JSON byte for byte")
    totals = {category: Fraction(0) for category in CATEGORIES}
    offset = 0
    tokens = counter.encoding.encode(text, disallowed_special=())
    for token in tokens:
        data = counter.encoding.decode_single_token_bytes(token)
        for category, count in Counter(labels[offset:offset + len(data)]).items():
            totals[category] += Fraction(count, len(data))
        offset += len(data)
    require(offset == len(labels) and sum(totals.values()) == len(tokens), "token attribution must cover complete text")
    return {"isolated_text_tokens": len(tokens), "category_token_equivalents": {key: round(float(value), 3) for key, value in totals.items()},
            "category_utf8_bytes": dict(Counter(labels)), "exact_duplicate_leaf_values": duplicates}


def audit_saved_checkpoints():
    calibration = json.loads((REPO / "analysis/calibration-v1.0.0.json").read_text())
    counter, records = NativeTokenizer(), []
    for record in calibration["records"]:
        raw = RawRun.open_existing(REPO / "runs/calibration", record["raw_run_id"])
        frozen = raw.load_frozen()
        require(frozen.sha256 == record["trajectory_sha256"], "calibration source hash differs")
        task_event = next(event for event in frozen.events if event.id.endswith("_task"))
        text = compile_fixed(build_state(frozen, json.loads(task_event.payload_json)["content"]))
        saved = canonical_json(json.loads((raw.path / "state.json").read_text()))
        require(text == saved, "reconstructed state differs from saved baseline")
        attribution = attribute(text, counter)
        require(attribution["isolated_text_tokens"] == record["native_handoff_counts"]["FIXED_STATE"]["count"], "baseline token count changed")
        records.append({"task_id": record["task_id"], "trajectory_sha256": frozen.sha256,
                        "fixed_state_sha256": text_digest(text), "full_history_tokens": counter.count(canonical_json(frozen.events)).count,
                        "provider_reported_usage": None, **attribution})
    return {"version": "token-attribution/1.0.0", "records": records,
            "method": "tiktoken 0.12.0/o200k_base complete isolated JSON; each token weight divided among labelled UTF-8 bytes",
            "interpretation": "total counts exact for local BPE encoding; category allocations estimated, rounded token-equivalents, not billed provider usage",
            "categories": {
                "substantive_statements": "first occurrences of goal/claims/action descriptions/changes/failures/retry text",
                "evidence_excerpts": "first occurrences of evidence excerpts and action-result strings (including visible source/test output)",
                "duplicated_content": "later exact repetitions of entire substantive/evidence leaf strings; excludes duplicated metadata and partial/semantic overlap",
                "identifiers_and_metadata": "IDs/hashes/source locations/timestamps/versions/statuses/confidence/scope; includes repeated full source-hash maps",
                "serialization_overhead": "field names, JSON punctuation/quotes and escape syntax"},
            "serializer_changed": False, "compression_implemented": False}
