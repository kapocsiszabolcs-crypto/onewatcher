#!/usr/bin/env python3
"""One.hu iPhone 16e 128 GB készletfigyelő GitHub Actions-höz."""

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from playwright.sync_api import sync_playwright


URL = "https://www.one.hu/okostelefonok?marka=Apple&tarhely=128"

PRODUCT_NAME = "iPhone 16e 128 GB"

NAVIGATION_TIMEOUT_MS = 60_000
PAGE_WAIT_MS = 5_000

DEBUG_SCREENSHOT = Path("debug.png")
DEBUG_HTML = Path("debug.html")


def save_debug(page):
    """Hibakeresési fájlok mentése."""
    try:
        page.screenshot(
            path=str(DEBUG_SCREENSHOT),
            full_page=True,
            timeout=15_000,
        )
        print(f"Képernyőkép mentve: {DEBUG_SCREENSHOT}")
    except Exception as exc:
        print(f"A képernyőkép mentése nem sikerült: {exc}")

    try:
        DEBUG_HTML.write_text(
            page.content(),
            encoding="utf-8",
        )
        print(f"HTML mentve: {DEBUG_HTML}")
    except Exception as exc:
        print(f"A HTML mentése nem sikerült: {exc}")


def send_email():
    """Értesítő e-mail küldése."""
    user = os.environ.get("SMTP_USER")
    pwd = os.environ.get("SMTP_PASS")
    to = os.environ.get("MAIL_TO")

    missing = [
        name
        for name, value in (
            ("SMTP_USER", user),
            ("SMTP_PASS", pwd),
            ("MAIL_TO", to),
        )
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Hiányzó GitHub Secrets / környezeti változók: "
            + ", ".join(missing)
        )

    msg = EmailMessage()

    msg["Subject"] = "iPhone 16e 128 GB KÉSZLETEN a One-nál!"
    msg["From"] = user
    msg["To"] = to

    msg.set_content(
        "Az iPhone 16e 128 GB készletállapota megváltozott.\n\n"
        "A One weboldala jelenleg ezt írja:\n"
        "Készleten\n\n"
        "Ellenőrizd az oldalon:\n"
        f"{URL}\n"
    )

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        timeout=30,
    ) as smtp:
        smtp.login(user, pwd)
        smtp.send_message(msg)

    print("Értesítő e-mail elküldve.")


def main():
    in_stock = False

    with sync_playwright() as pw:

        browser = pw.chromium.launch(headless=True)

        context = browser.new_context(
            locale="hu-HU",
            viewport
