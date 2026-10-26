# Contributing to TwitchFix / Как помочь проекту

Спасибо за интерес к проекту! Ниже — минимальный чеклист для PR.

## Development setup

```bash
git clone https://github.com/kayorissss/twitch-fix.git
cd twitch-fix
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt pytest
python -m pytest -q
python src/main.py
```

## Code style

- Python 3.11+, type hints for public functions/classes, docstrings in Russian or English.
- Keep UI code free of network calls: use `DiagnosticEngine` / `FixEngine` (QThreadPool).
- Every check inherits `BaseCheck` and returns `CheckResult`; every fix inherits `BaseFix`, uses `BackupManager` and returns `FixResult`.
- New UI strings go to `src/config/i18n.py` (`TR`), never hard-coded in both languages.
- Never log or report passwords, tokens, proxy credentials or Windows usernames.

## Adding a check

1. Create `src/core/diagnostics/my_check.py` with a `BaseCheck` subclass (`id`, `title_ru`, `title_en`, `icon`, `fix_id`, `run()`).
2. Register it in `CHECK_CLASSES` in `src/core/diagnostics/__init__.py`.
3. Add a card mapping on the dashboard if the quick status needs one.
4. Add unit tests for pure helpers in `tests/`.
5. If it can be repaired, add `src/core/fixes/my_fix.py`, register it in `src/core/fixes/__init__.py`, and make sure `requires_admin`/`windows_only` are correct.

## Pull requests

1. Fork → branch `feat/…` or `fix/…`.
2. Run `python -m pytest -q` and `python -m compileall -q src`.
3. Describe the problem, the fix and how you tested it (screenshots welcome).
4. Open a PR against `main`. GitHub Actions will run tests and the Windows build.

Bug reports: include the generated report (Report → Copy) and the log file, but remove any private data before posting.
