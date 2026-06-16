#!/usr/bin/env python3
"""Vault health checker. Run on cron, writes report to _health/."""
import frontmatter, glob, os, re, sys, tempfile
from datetime import datetime, timezone

VAULT_ROOT = os.environ.get("VAULT_PATH", os.path.expanduser("~/vault"))
REQUIRED_FIELDS = {"type", "created", "agent", "status", "tags"}

def _write_atomic(path, content, meta):
    post = frontmatter.Post(content, **meta)
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            frontmatter.dump(post, f)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise

def check_note(path):
    issues = []
    try:
        post = frontmatter.load(path)
        meta = post.metadata
        missing = REQUIRED_FIELDS - set(meta.keys())
        if missing:
            issues.append(f"missing fields: {', '.join(sorted(missing))}")
        if "tags" in meta and not isinstance(meta["tags"], list):
            issues.append("tags must be a list, not a string")
    except Exception as e:
        issues.append(f"parse error: {e}")
    return issues

def run_doctor():
    all_notes = glob.glob(os.path.join(VAULT_ROOT, "**/*.md"), recursive=True)
    all_notes = [p for p in all_notes if "_health" not in p and ".obsidian" not in p]
    note_names = {os.path.splitext(os.path.basename(p))[0] for p in all_notes}
    link_targets = set()
    bad = []
    for path in all_notes:
        issues = check_note(path)
        if issues:
            bad.append({"path": path, "issues": issues})
        try:
            with open(path, encoding="utf-8") as f:
                for m in re.findall(r'\[\[([^\]|#]+)', f.read()):
                    link_targets.add(m.strip())
        except Exception:
            pass
    orphans = len(note_names - link_targets)
    return {"scanned": len(all_notes), "bad": bad, "orphans_estimate": orphans}

def write_report(report):
    ts = datetime.now(timezone.utc)
    date_str = ts.strftime("%Y-%m-%d")
    path = os.path.join(VAULT_ROOT, "_health", f"health-{date_str}.md")
    lines = [
        f"# Vault Health — {date_str}", "",
        f"- Notes scanned: {report['scanned']}",
        f"- Notes with issues: {len(report['bad'])}",
        f"- Estimated orphans: {report['orphans_estimate']}", "",
    ]
    if report["bad"]:
        lines.append("## Issues found")
        for item in report["bad"]:
            lines.append(f"\n### `{os.path.basename(item['path'])}`")
            for iss in item["issues"]:
                lines.append(f"- {iss}")
    else:
        lines.append("## All notes OK ✅")
    meta = {"type": "health-report", "created": ts.isoformat(),
            "agent": "vault-doctor", "status": "complete", "tags": ["health", "system"]}
    _write_atomic(path, "\n".join(lines), meta)
    return path

if __name__ == "__main__":
    report = run_doctor()
    path = write_report(report)
    print(f"Report: {path}")
    print(f"Scanned {report['scanned']} | Issues {len(report['bad'])} | Orphans ~{report['orphans_estimate']}")
    if report["bad"]:
        sys.exit(1)
