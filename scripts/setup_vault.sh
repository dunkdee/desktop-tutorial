#!/bin/bash
# Creates the Obsidian vault folder structure on the VM.
VAULT_DIR="${VAULT_PATH:-$HOME/vault}"
echo "Setting up vault at $VAULT_DIR"
mkdir -p \
  "$VAULT_DIR/00-inbox" \
  "$VAULT_DIR/10-research" \
  "$VAULT_DIR/20-deals" \
  "$VAULT_DIR/30-surplus-cases" \
  "$VAULT_DIR/40-manual" \
  "$VAULT_DIR/90-meta/templates" \
  "$VAULT_DIR/_attachments" \
  "$VAULT_DIR/_health"

# .gitignore so Obsidian workspace files stay local
cat > "$VAULT_DIR/.gitignore" << 'EOF'
.obsidian/workspace*
.obsidian/graph.json
.trash/
*.tmp
_health/
EOF

# Starter template for agent notes
cat > "$VAULT_DIR/90-meta/templates/agent-note.md" << 'EOF'
---
type:
title:
created:
agent:
status: raw
tags: []
---

<!-- content here -->
EOF

echo "Vault ready at $VAULT_DIR"
ls -la "$VAULT_DIR"
