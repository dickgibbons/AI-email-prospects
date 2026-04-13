#!/usr/bin/env python3
"""EPAM Outreach — Daily orchestrator.

Usage:
    python run_daily.py            # full run
    python run_daily.py --dry-run  # print what would happen, no writes
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents.selector import select_prospects, read_all_rows
from agents.researcher import research_prospect
from agents.writer import generate_touch
from agents.publisher import publish
from agents.reminder import get_due_today, send_reminder

log = logging.getLogger("outreach")


def setup_logging():
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt)


def run(dry_run: bool = False):
    setup_logging()
    log.info("=== EPAM Outreach daily run (dry_run=%s) ===", dry_run)

    all_rows = read_all_rows()
    prospects = select_prospects(all_rows)

    if not prospects:
        log.info("No eligible prospects today.")
    else:
        log.info("Processing %d prospect(s)...", len(prospects))

    results = []

    for i, prospect in enumerate(prospects, 1):
        name = prospect.get("name", "?")
        company = prospect.get("company", "?")
        touch_num = prospect.get("lastTouchSent", 0) + 1
        log.info("[%d/%d] %s at %s — touch %d", i, len(prospects), name, company, touch_num)

        if dry_run:
            log.info("  DRY RUN — would research, generate, and publish touch %d", touch_num)
            results.append({"prospect": name, "company": company, "touch": touch_num, "status": "dry_run"})
            continue

        try:
            research = research_prospect(prospect)
            log.info("  Research done: %s", research.get("recommendedSubjectFragment", ""))

            email = generate_touch(prospect, research)
            log.info("  Email generated: subject=%s", email.get("subject", ""))

            doc_link = publish(prospect, email)
            log.info("  Published: %s", doc_link)

            results.append({
                "prospect": name,
                "company": company,
                "touch": touch_num,
                "subject": email.get("subject", ""),
                "doc_link": doc_link,
                "status": "ok",
            })
        except Exception:
            log.exception("  FAILED for %s at %s", name, company)
            results.append({"prospect": name, "company": company, "touch": touch_num, "status": "error"})

    if not dry_run:
        log.info("--- Sending reminder ---")
        try:
            refreshed_rows = read_all_rows()
            due = get_due_today(refreshed_rows)
            send_reminder(due)
        except Exception:
            log.exception("Failed to send reminder email")

    succeeded = sum(1 for r in results if r["status"] == "ok")
    failed = sum(1 for r in results if r["status"] == "error")
    log.info(
        "=== Done. Processed: %d, Succeeded: %d, Failed: %d ===",
        len(results), succeeded, failed,
    )

    return results


def main():
    parser = argparse.ArgumentParser(description="EPAM Outreach daily orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
