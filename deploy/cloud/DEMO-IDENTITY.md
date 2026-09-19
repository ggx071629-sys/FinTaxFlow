# Explicit demo identities (2026-09-20)

All seeded companies and counterparties use fictional labels and DEMO-prefixed 18-character identifiers. These are test identifiers, not registered tax identities. Website notices and both invoice/receipt PDFs identify simulation explicitly. Do not enter real financial or tax data.

Existing cloud data is updated with `python /app/deploy/update_demo_identities.py --apply` in a maintenance container with the API stopped, **after a fresh database and invoice/RPA file backup**. Without --apply, DB changes are rolled back and disk files remain unchanged.

The update matches exact legacy name/identifier pairs in the approved synthetic catalog; company IDs, ownership, generation, monetary values, task states, submission counts and receipt/file IDs remain unchanged. Unknown identities are untouched. Invoice and receipt PDFs are regenerated with disclosures. Original imported files and historical RPA evidence are preserved as original evidence; their old sample text is not rewritten. Do not seed, reset or delete existing records.

`Dockerfile.update` overlays application code and portal assets onto the immutable previously verified API image (Python/Chrome dependency layer retained). Supply BASE_IMAGE by SHA256 and REVISION from the Git commit. Build H5 with `VITE_CLOUD_DEPLOYMENT=true VITE_API_BASE_URL=https://tax.gavingongxin.com/api npm run build:h5`; lockfile includes the prior Intlify/Vite fixes and .npmrc records the UniApp peer compatibility exception. Use the existing service topology, volumes and TLS configuration.

Keep the old release and backups. If the update fails, keep the API stopped, restore the matching database/files backup, then select the old release and restart its API. Never replay declaration submissions during rollback.
