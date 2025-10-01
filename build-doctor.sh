#!/usr/bin/env bash
set -euo pipefail
echo "👑 Dominion’s Ark: Doctor + Backup Setup..."

# Ensure we’re in the repo
if [ ! -d "$HOME/ai/.git" ]; then
  echo "⚠️ Not in repo, switching to ~/ai..."
  cd ~/ai || { echo "❌ Repo not found at ~/ai"; exit 1; }
fi

# Empire Doctor command
sudo tee /usr/local/bin/empire-doctor >/dev/null <<'EOF'
#!/usr/bin/env bash
echo "=== Dominion Empire Doctor ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo
for svc in daily-content.service shopify-sync.service; do
  if systemctl list-unit-files | grep -q "$svc"; then
    echo "== $svc =="
    systemctl status $svc --no-pager -l | head -n 15 || true
    journalctl -u $svc -n 20 --no-pager || true
    echo
  fi
done
EOF
sudo chmod +x /usr/local/bin/empire-doctor

# Backup sync to GitHub
git add .
git commit -m "Live sync: Dominion’s Ark deployment after system upgrade" || true
git push origin main || true

echo "✅ Doctor + Backup complete."
echo "Use: empire-doctor   # to check containers + logs"
