"""Check a report record and comment: python3 validate.py publication.json comment.md."""

import hashlib
import json
import re
import sys
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


record_path, body_path = map(Path, sys.argv[1:])
record = json.loads(record_path.read_text())
body = body_path.read_text()
publication = record["publication"]
require(record["schema_version"] == 1, "Unsupported schema")
require(record["id"] == str(uuid.uuid5(uuid.NAMESPACE_URL, record["identity"])), "Report identity mismatch")
digest = hashlib.sha256(body.encode()).hexdigest()
require(publication["body_sha256"] == digest, "Comment content changed")
require(record["id"] in body, "Comment lacks report identifier")
sources = {source["id"] for source in record["sources"]}
identifiers = []


def inspect(value):
    if isinstance(value, dict):
        if "id" in value:
            identifiers.append(value["id"])
            require(uuid.UUID(value["id"]).version in {5, 7}, "Invalid identifier version")
        if "source_id" in value:
            require(value["source_id"] in sources, "Missing evidence source")
        if "source_ids" in value:
            require(set(value["source_ids"]) <= sources, "Missing claim source")
        for child in value.values():
            inspect(child)
    elif isinstance(value, list):
        for child in value:
            inspect(child)


inspect(record)
require(len(identifiers) == len(set(identifiers)), "Duplicate identifiers")
sample = record["sample"]
counts = Counter(row["status"] for row in record["observations"])
require(counts == {"failed": sample["failure_count"], "success": sample["success_count"]}, "Capture counts differ")
successful_targets = set()
for row in record["observations"]:
    require(sample["start_inclusive"] <= row["created_at"] <= row["observed_at"] <= sample["end_inclusive"], "Capture outside sample")
    require(row["created_source_line"] < row["source_line"], "Request and result order invalid")
    require(type(row["had_screenshot"]) is bool and type(row["had_accessibility_text"]) is bool, "Capture flags must be booleans")
    if row["status"] == "failed":
        require(row["target"] == "com.google.Chrome", "Unexpected failing target")
        require(row["failure_reason"] == "start_request_failed:computer_use:-10005", "Different failure signature")
        require(not row["had_screenshot"] and not row["had_accessibility_text"], "Different capture stage")
    else:
        require(row["had_screenshot"] and row["had_accessibility_text"] and row["failure_reason"] is None, "Incomplete successful result")
        successful_targets.add(row["target"])
controls = record["delivered_controls"]
require(successful_targets == {item["bundle_identifier"] for item in controls}, "Delivered controls differ from successful targets")
require(len(controls) == len(successful_targets) == sample["successful_target_count"], "Control count mismatch")
require(all(item["image_received"] and item["accessibility_text_received"] for item in controls), "Control attachment missing")
require(f'| Chrome | {sample["failure_count"]} failures |' in body, "Comment failure count differs")
require(f'all {len(controls)} successful applications' in body, "Comment comparison count differs")
target_counts = Counter(row["target"] for row in record["observations"] if row["status"] == "success")
names = {item["name"]: item["bundle_identifier"] for item in controls}
table_names = []
for targets, count in re.findall(r"^\| (.*?) \| (\d+) success(?:es)?(?: each)? \| Both present \|$", body, re.MULTILINE):
    for name in targets.split(", "):
        require(name in names and target_counts[names[name]] == int(count), "Comment per-application count differs")
        table_names.append(name)
require(len(table_names) == len(set(table_names)) and set(table_names) == set(names), "Comment target table differs")

# machine_contract 97c0c633-d01f-5023-9868-f2939ac39ebd:
# reviewed -> published -> verified; new evidence permits verified -> reviewed.
# Verification here checks the receipt's consistency; live GitHub readback is separate.
allowed = {(None, "reviewed"), ("reviewed", "published"), ("published", "verified"), ("verified", "reviewed")}
previous, times = None, []
for event in record["events"]:
    require(event["from"] == previous and (previous, event["to"]) in allowed, "Invalid publication transition")
    identifier = uuid.UUID(event["id"])
    timestamp = datetime.fromisoformat(event["recorded_at"].replace("Z", "+00:00"))
    require(identifier.version == 7 and abs(timestamp.timestamp() * 1000 - identifier.time) < 1, "Event identifier time mismatch")
    times.append(timestamp)
    previous = event["to"]
require(times == sorted(times), "Events out of order")
require(previous == publication["status"], "Publication state differs from event history")
require(publication["shared_root_cause_confirmed"] is False, "Unsupported root-cause claim")
if previous == "verified":
    require(record["events"][-1]["body_sha256"] == digest, "Readback refers to another revision")
    require(publication["url"].endswith(f'#issuecomment-{publication["comment_id"]}'), "Comment link mismatch")

public_text = body + record_path.read_text()
require(not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", public_text), "Possible email address")
for forbidden in ("/Users/", "/Volumes/", "/var/folders/", "chatgpt.com/c/", "chatgpt.com/share/", "github.com/settings/", "discord.com/channels/", "![", "window-title", "requestId="):
    require(forbidden not in public_text, "Private context or raw attachment reference found")
print(json.dumps({"result": "PASS", "state": previous, "failures": counts["failed"], "successes": counts["success"], "comparison_applications": len(controls), "body_sha256": digest}))
