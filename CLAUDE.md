# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Desktop application (French UI, XPF / Franc Pacifique currency) for managing customer
credit notes ("avoirs") for **Quincaillerie Calédonienne** in Nouméa, New Caledonia.
Built with Python + Tkinter, backed by a SQLite database, and distributed as a Windows
`.exe` via PyInstaller. Developed by STOYANN. All code, comments, and UI strings are in
French — match that when editing.

## Commands

```powershell
# Install dependencies (Python 3.8+; tkinter and sqlite3 ship with Python)
pip install -r requirements.txt

# Run the app from source
python main.py

# Inspect / switch which database the app uses (writes shared network config)
python config_bdd.py --show            # show active DB folder + dev/test state
python config_bdd.py --prod            # point ALL machines at production DB
python config_bdd.py --test            # point ALL machines at shared TEST DB
python config_bdd.py --dev-test [dir]  # switch THIS machine only to a test DB
python config_bdd.py --dev-off         # revert THIS machine to shared config

# Seed a database with avoirs in every status (for testing the dashboard)
python test_data.py                    # uses the app's active DB
python test_data.py "C:\path\avoirs.db"
python test_data.py --reset            # delete test avoirs first

# Build the Windows executable (output in dist/)
pyinstaller avoir_qc_V_1.0.spec
```

There is **no test framework, linter, or CI** in this repo. `test_data.py` is a data-seeding
script, not an automated test suite. Verify changes by running the app against a dev/test DB.

## Architecture

Layered, with strict dependency direction `gui → models → database → config`:

- **`config/`** — pure configuration and path resolution, no business logic.
  - `settings.py` — all constants: `USER_ROLES`, `AVOIR_STATUS`, `AVOIR_TYPES`, `PERMISSIONS`
    (role → allowed actions), `SMTP_CONFIG`, `REPORT_CONFIG`, error/success message templates,
    plus `format_currency()`/`parse_currency()` helpers (XPF, space thousands separator, `F` suffix).
  - `paths.py` — resolves the active database folder and creates working dirs (see "Database location" below).
  - `email_templates.py` — HTML email bodies.
- **`database/connection.py`** — the `Database` class: SQLite schema creation, migrations, and
  low-level queries. This is the single source of truth for the schema.
- **`models/`** — business logic operating on a `Database` instance.
  - `avoir_manager.py` — `AvoirManager`: create/use/cancel/block/force avoirs, generate numbers,
    statistics, list/filter queries. Holds the core credit-note lifecycle rules.
  - `user_manager.py` — `UserManager`: authentication (SHA-256), user CRUD, role management.
- **`services/`** — side-effecting integrations.
  - `email_service.py` — `EmailService`: SMTP send + background reminder worker thread.
  - `pdf_creator.py` — `PDFCreator`: reportlab-based avoir PDFs.
- **`gui/`** — `login_window.py`, `splash_screen.py`, `database/initial_setup.py` (first-run dialog).
- **`gui_main.py`** (root, ~4600 lines) — `MainWindow`, the primary application UI after login,
  plus `UtilisationDialog` and `ModernButton`. This is where most UI feature work happens.
- **`main.py`** — entry point. `ApplicationManager` orchestrates the lifecycle: splash screen →
  staged background loading → login → main window, in a **re-login session loop** (`run_sessions`)
  so logout returns to the login screen without exiting the process.

### Important conventions

- **Only the last, uncommented class/function in a file is live.** Several files (`main.py`,
  `user_manager.py`, `config/settings.py`) keep large blocks of earlier commented-out versions
  above the active code. When editing, jump to the last non-commented definition (e.g. active
  `main.py` code starts ~line 579; active `UserManager` ~line 583). Don't edit the dead copies.
- **Always use the status/role/type constants** from `config/settings.py` (`AVOIR_STATUS['EXPIRE']`,
  etc.) rather than string literals — mismatches like `'expire'` vs `'expir'` are a known source of bugs
  and `test_data.py` deliberately reuses these same constants for that reason.
- **Currency is XPF, integer francs**, formatted with `format_currency()` (space-separated, `F` suffix).
- Permissions are enforced by checking `PERMISSIONS[role]` — roles are `super_user`, `responsable`,
  `comptabilite` (currently same rights as responsable), `vendeur` (most limited).

### Database location (critical)

The app does **not** use a local DB by default. `config/paths.py` resolves the DB folder in priority order:

1. **Local dev/test override** — `~/.module_avoir_local.json` on THIS machine only (set via
   `config_bdd.py --dev-test`). Lets you develop against a test DB while other machines stay on production.
2. **Shared network config** — `base_path` in `\\192.168.0.250\Bases\module_avoir_config.json`.
   This file is shared by every machine; changing it changes the DB for **all** machines.
3. **Default** — `\\192.168.0.250\Bases\db_module_avoir_qc\avoirs.db` (production).

The absence of `module_avoir_config.json` on the network share signals "first run", triggering the
initial super-user + DB-path setup dialog. **When developing, always switch to a dev/test DB first**
(`python config_bdd.py --dev-test`) so you never touch production. Schema changes belong in
`Database.create_tables()` / `update_existing_tables()` (additive `ALTER TABLE` migrations only).

### Avoir (credit-note) domain model

- Avoirs default to **90-day validity** and can be used **partially**: a partial use creates a
  **child avoir** (`avoir_parent_id`, `est_avoir_enfant`) for the remaining balance, recorded in
  `historique_utilisation`. Core logic in `AvoirManager.use_avoir()` / `create_avoir_enfant()`.
- Statuses: `actif`, `utilise`, `utilise_partiellement`, `expire`, `annule`, `supprime`, `bloque`.
- An **expired** avoir can be "forced" through by a responsable (recorded in `forcage_autorise_par`);
  a **blocked** avoir requires a comment and sends the client to accounting.
- **Expiration reminders** are sent by a background worker thread in `EmailService`. Reminder sends
  are made idempotent across concurrently-running machines via atomic `Database.claim_reminder()` /
  `release_reminder()` (flip a `0→1` flag, only one caller wins), backed by an `email_history` check.

## Notes

- SQLite connections use `timeout=30` + `PRAGMA busy_timeout=30000` because the DB lives on a
  shared network drive accessed by multiple machines. Pass `thread_safe=True` to `Database` for the
  background email worker (opens a fresh connection per query).
- The reference user manual is `Manuel_Utilisateur_Avoirs.docx`; a CSV import template for users is
  `modele_utilisateurs.csv`.
