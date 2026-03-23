# Snowbound LLC — Migration Plan Index

Migration from Google Apps Script + Google Sheets to Python/Flask on PythonAnywhere.

## Phases

| Phase | Document | Status |
|---|---|---|
| 1 | [Infrastructure Setup](phase-1-infrastructure.md) | Not started |
| 2 | [Seed Database](phase-2-seed-database.md) | Not started |
| 3 | [Build Core Routes](phase-3-core-routes.md) | Not started |
| 4 | [Parallel Testing](phase-4-parallel-testing.md) | Not started |
| 5 | [Deploy & Cutover](phase-5-cutover.md) | Not started |
| 6 | [Post-Migration Enhancements](phase-6-enhancements.md) | Optional |

## Summary

- **Source:** Google Apps Script web app + Google Sheets backend (~10 owner families, Breckenridge CO condo)
- **Destination:** Flask + SQLite on PythonAnywhere
- **Driver:** Chromium multi-account bug breaks GAS web apps; fix is impossible at the code level
- **Key constraint:** Elderly user base — magic link auth, same visual calendar layout, phone/tablet friendly

## Reference Documents

- [CLAUDE.md](../CLAUDE.md) — Full project spec and architecture
- [SnowboundMigrationDesign.md](../SnowboundMigrationDesign.md) — Detailed design document
- [generic-table-browser-requirements.md](../generic-table-browser-requirements.md) — Admin table browser spec
- [Requirements.md](../Requirements.md) — Original requirements
