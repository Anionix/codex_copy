#!/usr/bin/env python3
"""Validate a public issue body and its publication receipt without network access."""

import datetime as dt
import hashlib
import json
import re
import sys
import uuid
from pathlib import Path


HEADINGS = (
    "What version of the Codex App are you using (From “About Codex” dialog)?",
    "What subscription do you have?",
    "What platform is your computer?",
    "What issue are you seeing?",
    "What steps can reproduce the bug?",
    "What is the expected behavior?",
    "Additional information",
)
STATES = ("draft", "reviewed", "published", "verified")
LIMITATIONS = {
    "fresh_reproduction": False,
    "root_cause": "unconfirmed",
    "original_running_version": "unconfirmed",
    "subscription": "not_recorded",
}
CREDENTIAL_PATTERNS = {
    "OpenAI secret key": r"\bsk-[A-Za-z0-9_-]{16,}",
    "GitHub access token": r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})",
    "AWS access key": r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "authorization credential": r"(?i)\b(?:bearer|authorization\s*:\s*basic)\s+[A-Za-z0-9._~+/=-]{12,}",
    "private key": r"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----",
    "assigned secret": r'''(?ix)["']?\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password)["']?\s*[:=]\s*["']?[A-Za-z0-9_./+=-]{12,}''',
}


def validate(body_bytes, receipt):
    errors = []
    counts = {"sources": 0, "claims": 0, "events": 0}
    seen_ids = set()

    def require(condition, message):
        if not condition:
            errors.append(message)

    def mapping(value, label):
        require(isinstance(value, dict), label + " must be an object")
        return value if isinstance(value, dict) else {}

    def sequence(value, label):
        require(isinstance(value, list), label + " must be a list")
        return value if isinstance(value, list) else []

    def identity(record, label, version):
        value = record.get("id")
        try:
            parsed = uuid.UUID(value) if isinstance(value, str) else None
        except ValueError:
            parsed = None
        if parsed is None:
            errors.append(label + ".id must be a UUID")
            return None
        require(str(parsed) == value, label + ".id must use canonical lowercase form")
        require(parsed.version == version and parsed.variant == uuid.RFC_4122,
                label + ".id must be UUID version " + str(version))
        require(parsed not in seen_ids, label + ".id duplicates another record")
        seen_ids.add(parsed)
        if version == 5:
            name = record.get("identity_name")
            require(isinstance(name, str) and bool(name.strip()),
                    label + ".identity_name must be a nonempty string")
            if isinstance(name, str):
                require(parsed == uuid.uuid5(uuid.NAMESPACE_URL, name),
                        label + ".id does not match identity_name in the URL namespace")
        return parsed

    try:
        body = body_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return counts, ["Issue body must be valid UTF-8"]
    receipt = mapping(receipt, "receipt")
    require(receipt.get("schema_version") == "1.0", "schema_version must be 1.0")

    report = mapping(receipt.get("report"), "report")
    report_id = identity(report, "report", 5)
    require(isinstance(report.get("title"), str) and bool(report.get("title", "").strip()),
            "report.title must be a nonempty string")
    require(report.get("body_sha256") == hashlib.sha256(body_bytes).hexdigest(),
            "report.body_sha256 does not match the supplied body bytes")
    require(report_id is not None and str(report_id) in body, "Report identifier is missing from the body")
    for heading in HEADINGS:
        require(re.search(r"^### " + re.escape(heading) + r"\r?$", body, re.MULTILINE) is not None,
                "Missing official template heading: " + heading)
    require(re.search(r"[\u3040-\u30ff\u31f0-\u31ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f\U00020000-\U000323af]", body) is None,
            "Issue body contains Japanese kana or CJK characters; English is required")
    require(re.search(r"(?i)(?:https?://)?(?:www\.)?chatgpt\.com/(?:share|c)(?:/|[?#\s)>]|$)", body) is None,
            "Issue body contains a prohibited conversation link")
    for label, pattern in CREDENTIAL_PATTERNS.items():
        require(re.search(pattern, body) is None, "Issue body contains a possible " + label)

    sources = sequence(receipt.get("sources"), "sources")
    claims = sequence(receipt.get("claims"), "claims")
    events = sequence(receipt.get("events"), "events")
    counts.update(sources=len(sources), claims=len(claims), events=len(events))
    source_ids = set()
    for index, item in enumerate(sources):
        label = "sources[" + str(index) + "]"
        source = mapping(item, label)
        parsed = identity(source, label, 5)
        if parsed is not None:
            source_ids.add(str(parsed))
    for index, item in enumerate(claims):
        label = "claims[" + str(index) + "]"
        claim = mapping(item, label)
        identity(claim, label, 5)
        refs = sequence(claim.get("source_ids"), label + ".source_ids")
        for ref_index, ref in enumerate(refs):
            require(isinstance(ref, str) and ref in source_ids,
                    label + ".source_ids[" + str(ref_index) + "] references an unknown source")

    # Machine contract: draft -> reviewed -> published -> verified.
    # UUID version 5 identifies information; version 7 follows recorded event time.
    # Verification proves receipt consistency, not fresh reproduction or root cause.
    require([event.get("state") if isinstance(event, dict) else None for event in events] == list(STATES),
            "events must follow draft -> reviewed -> published -> verified exactly")
    previous_time = None
    epoch = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
    for index, item in enumerate(events):
        label = "events[" + str(index) + "]"
        event = mapping(item, label)
        parsed = identity(event, label, 7)
        raw_time = event.get("recorded_at")
        try:
            if not isinstance(raw_time, str) or "T" not in raw_time:
                raise ValueError
            recorded = dt.datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            if recorded.tzinfo is None or recorded.utcoffset() is None:
                raise ValueError
            recorded = recorded.astimezone(dt.timezone.utc)
        except (ValueError, OverflowError):
            errors.append(label + ".recorded_at must be a timezone-aware ISO 8601 timestamp")
            continue
        require(previous_time is None or recorded >= previous_time,
                label + ".recorded_at precedes the previous event")
        previous_time = recorded
        elapsed = recorded - epoch
        microseconds = (elapsed.days * 86400 + elapsed.seconds) * 1000000 + elapsed.microseconds
        if parsed is not None:
            require(abs((parsed.int >> 80) * 1000 - microseconds) <= 1000,
                    label + ".id timestamp differs from recorded_at by more than 1 millisecond")

    publication = mapping(receipt.get("publication"), "publication")
    number = publication.get("issue_number")
    require(type(number) is int and number > 0, "publication.issue_number must be a positive integer")
    require(publication.get("repository") == "openai/codex", "publication.repository must be openai/codex")
    require(publication.get("issue_url") == "https://github.com/openai/codex/issues/" + str(number),
            "publication.issue_url does not match its repository and issue number")
    require(publication.get("body_verified") is True, "publication.body_verified must be true")
    require(publication.get("requested_labels") == ["app"], "publication.requested_labels must be [app]")
    observed_labels = sequence(publication.get("observed_labels"), "publication.observed_labels")
    require(all(isinstance(label, str) and bool(label.strip()) for label in observed_labels),
            "publication.observed_labels must contain nonempty strings")
    # A requested label need not be observed; retain an honest empty readback.

    fork = mapping(receipt.get("fork"), "fork")
    require(fork.get("repository") == "Anionix/codex_copy", "fork.repository must be Anionix/codex_copy")
    require(fork.get("parent") == "openai/codex", "fork.parent must be openai/codex")
    before = fork.get("main_before")
    after = fork.get("main_after")
    require(isinstance(before, str) and bool(re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", before)),
            "fork.main_before must be a full Git commit identifier")
    require(before == after, "Fork main changed between the recorded observations")
    limitations = mapping(receipt.get("limitations"), "limitations")
    for key, expected in LIMITATIONS.items():
        actual = limitations.get(key)
        require(type(actual) is type(expected) and actual == expected,
                "limitations." + key + " must remain " + json.dumps(expected))
    return counts, errors


def main():
    counts = {"sources": 0, "claims": 0, "events": 0}
    if len(sys.argv) != 3:
        errors = ["Usage: validate_publication.py issue_body_file publication_json_file"]
    else:
        try:
            body_bytes = Path(sys.argv[1]).read_bytes()
            receipt = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
            counts, errors = validate(body_bytes, receipt)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            errors = ["Cannot read the supplied files: " + str(error)]
    result = {"status": "failed" if errors else "passed", "counts": counts, "errors": errors}
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
