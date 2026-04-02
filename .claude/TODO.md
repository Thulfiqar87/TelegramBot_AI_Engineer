# AI Site Coordinator — Audit To-Do List
**Last updated:** 2026-04-02

---

## CRITICAL
- [x] **#1** `models.py` / `main.py` — UTC vs Baghdad timezone mismatch loses logs
  - Added `_utcnow()`, `_baghdad_date_str()`, `_today_start_utc()` helpers; all DB writes use UTC, all queries use UTC boundaries
- [x] **#2** `report.html` — Unclosed `<div>` breaks entire report structure
  - Fixed all section divs; each section is now properly opened and closed
- [x] **#3** `main.py` — Photo timestamps shown in UTC, not Baghdad time
  - Timestamps now converted from UTC → Baghdad before display in report

## HIGH
- [x] **#4** `main.py` — Report failures are silent (no Telegram notification)
  - Added `context.bot.send_message` in the except block of `generate_daily_report`
- [x] **#5** `main.py` — `ReportCounter` has no concurrency guard
  - Replaced read-modify-write with atomic SQLite `INSERT ... ON CONFLICT DO UPDATE`
- [x] **#6** `config.py` / `ai_engine.py` — Optional `OPENAI_API_KEY` fails silently at runtime
  - `OPENAI_API_KEY` is now a required `str` field; missing it fails at startup with a clear error

## MEDIUM
- [x] **#7** `schemas.py` — Dead file, nothing imports it → **deleted**
- [x] **#8** `database.py` — `get_db` is unused → **removed**
- [x] **#9** `pdf_generator.py` — CSS read is blocking and repeated every report
  - CSS now cached in `start_browser()` via `asyncio.to_thread`; `generate_report` uses `self._css`
- [x] **#10** `config.py` — Dead `OP_USERNAME` / `OP_PASSWORD` fields → **removed**
- [x] **#11** `requirements.txt` — `requests` is unused → **removed**
- [x] **#12** `ai_engine.py` — `get_safety_advice` has no `max_tokens` cap → added `max_tokens=120`
- [x] **#13** `main.py` — `set_safety_channel` silently ignores unauthorized users → added denial reply

## LOW
- [x] **#14** `config.py` — `raise e` loses original traceback → changed to bare `raise`
- [x] **#15** Two conflicting docker-compose files → **deleted `docker-compose.yml`**, kept `compose.yaml`
- [x] **#16** `Dockerfile` — Python 3.12 → updated to `python:3.13-slim`
- [x] **#17** `report.html` — External CDN icons replaced with inline Unicode emoji (🌡️ 💨)
- [x] **#18** No `.gitignore` → **created** with `.env`, `venv/`, `data/`, `__pycache__/`, etc.
