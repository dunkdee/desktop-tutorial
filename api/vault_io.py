import os, tempfile, uuid, re
from datetime import datetime, timezone

try:
    import frontmatter
    _HAS_FRONTMATTER = True
except ImportError:
    _HAS_FRONTMATTER = False

VAULT_ROOT = os.environ.get("VAULT_PATH", "/vault")

LANES = {
    "inbox":    "00-inbox",
    "research": "10-research",
    "deals":    "20-deals",
    "surplus":  "30-surplus-cases",
    "manual":   "40-manual",
    "meta":     "90-meta",
    "health":   "_health",
}


def _slug(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower())[:40].strip("-")


def write_note_atomic(path, content, metadata):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    if _HAS_FRONTMATTER:
        post = frontmatter.Post(content, **metadata)
        fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                frontmatter.dump(post, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    else:
        # Fallback: plain YAML header without python-frontmatter
        header = "---\n"
        for k, v in metadata.items():
            header += f"{k}: {v!r}\n"
        header += "---\n\n"
        fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(header + content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise


def create_note(lane, title, content, agent, note_type, tags=None, extra_meta=None):
    ts = datetime.now(timezone.utc)
    filename = f"{ts.strftime('%Y-%m-%d')}_{_slug(title)}_{str(uuid.uuid4())[:8]}.md"
    lane_dir = LANES.get(lane, lane)
    path = os.path.join(VAULT_ROOT, lane_dir, filename)
    metadata = {
        "type": note_type,
        "title": title,
        "created": ts.isoformat(),
        "agent": agent,
        "status": "raw",
        "tags": tags or [],
    }
    if extra_meta:
        metadata.update(extra_meta)
    write_note_atomic(path, content, metadata)
    return path


def list_lane(lane, status_filter=None):
    lane_dir = LANES.get(lane, lane)
    lane_path = os.path.join(VAULT_ROOT, lane_dir)
    if not os.path.isdir(lane_path):
        return []
    notes = []
    for fname in sorted(os.listdir(lane_path)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(lane_path, fname)
        meta = {"filename": fname, "path": fpath}
        if _HAS_FRONTMATTER:
            try:
                with open(fpath) as f:
                    post = frontmatter.load(f)
                meta.update(post.metadata)
            except Exception:
                pass
        if status_filter and meta.get("status") != status_filter:
            continue
        notes.append(meta)
    return notes
