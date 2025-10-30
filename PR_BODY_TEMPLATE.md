# PR: Import single n8n workflow from /tmp (template)

Summary
- This PR adds automation to safely import n8n workflows after the n8n service reports healthy.
- It includes:
  - scripts/repo-audit.sh       (audit)
  - scripts/health-and-import.sh (health-checked importer)
  - .github/workflows/build-and-deploy.yml (CI template)
  - docs/runbook.md (runbook + rollback instructions)

Checklist (one-job-per-PR, small auditable change)
- [ ] I have created a timestamped backup before making imports: /opt/dominion/n8n_data/backup-*.tar.gz
- [ ] This change is reversible by restoring the backup tarball
- [ ] No secret values are included in this PR. Placeholders used: <<SECRET:NAME>>
- [ ] Secrets file path referenced (not committed): /opt/dominion/infra/.env.n8n.secrets
- [ ] I have tested the audit script locally: bash ./scripts/repo-audit.sh
- [ ] CI workflow is provided as a placeholder; registry/deploy credentials are managed via repository secrets

Rollback procedure
- Restore from backup tarball: tar xzf /opt/dominion/n8n_data/backup-n8n-<timestamp>.tar.gz -C /
- Restart services: docker-compose -f /opt/dominion/stack/docker-compose.yml down && docker-compose -f /opt/dominion/stack/docker-compose.yml up -d

Testing
- Run audit script: bash ./scripts/repo-audit.sh
- Verify audit-report-<timestamp>.txt is generated
- Check that no secret values are printed (only file paths and placeholders)

Documentation
- See docs/runbook.md for full operational procedures
- See scripts/repo-audit.sh comments for usage and safety notes
