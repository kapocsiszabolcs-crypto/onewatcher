#!/usr/bin/env python3
"""One.hu iPhone 16e 128 GB készletfigyelő GitHub Actions-höz."""

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from playwright.sync_api import sync_playwright


URL = "https://www.one.hu/okostelefonok?marka=Apple&tarhely=128"

PRODUCT_NAME = "iPhone 16 128 GB"

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
            viewport={
                "width": 1440,
                "height": 1600,
            },
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        page = context.new_page()
        page.set_default_timeout(10_000)

        try:

            print(f"Oldalbetöltés: {URL}")

            response = page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=NAVIGATION_TIMEOUT_MS,
            )

            if response and response.status >= 400:
                save_debug(page)
                raise RuntimeError(
                    f"A One.hu HTTP {response.status} hibát adott."
                )

            page.wait_for_timeout(PAGE_WAIT_MS)

            # Cookie ablak kezelése, ha megjelenik
            cookie_labels = (
                "Összes elfogadása",
                "Elfogadom",
                "Elfogadás",
                "Rendben",
                "OK",
                "Accept all",
            )

            for label in cookie_labels:
                try:
                    button = page.get_by_role(
                        "button",
                        name=label,
                    ).first

                    if button.is_visible():
                        button.click(timeout=2000)
                        print(
                            f"Cookie/pop-up ablak kezelve: {label}"
                        )
                        page.wait_for_timeout(1000)
                        break

                except Exception:
                    continue

            # Várunk arra, hogy a termék neve bekerüljön a DOM-ba
            print(
                f"Termék keresése: {PRODUCT_NAME}"
            )

            try:
                page.get_by_text(
                    PRODUCT_NAME,
                    exact=False,
                ).first.wait_for(
                    state="visible",
                    timeout=20_000,
                )

            except Exception:
                save_debug(page)
                raise RuntimeError(
                    f"A termék nem található az oldalon: "
                    f"{PRODUCT_NAME}"
                )

            #
            # A teljes DOM-ból olyan elemeket keresünk,
            # amelyek tartalmazzák a termék nevét.
            #
            # Ezek közül a legkisebb olyan konténert keressük,
            # amelyben a készletállapot is megtalálható.
            #

            product_elements = page.get_by_text(
                PRODUCT_NAME,
                exact=False,
            )

            print(
                f"Talált '{PRODUCT_NAME}' elemek száma: "
                f"{product_elements.count()}"
            )

            stock_text = None

            for i in range(product_elements.count()):

                product = product_elements.nth(i)

                try:

                    # Felfelé haladunk a DOM-ban,
                    # amíg megtaláljuk a termékkártyát.
                    container = product.locator(
                        "xpath=ancestor::*["
                        ".//*[contains(normalize-space(.), "
                        "'Nincs készleten')] "
                        "or "
                        ".//*[normalize-space(.)='Készleten']"
                        "][1]"
                    )

                    if container.count() == 0:
                        continue

                    text = container.inner_text()

                    print(
                        "Termékkártya megtalálva."
                    )

                    if "Nincs készleten" in text:
                        stock_text = "Nincs készleten"
                        break

                    if "Készleten" in text:
                        stock_text = "Készleten"
                        break

                except Exception:
                    continue

            # Debug fájl minden futásnál
            save_debug(page)

            if stock_text is None:
                raise RuntimeError(
                    "A terméket megtaláltam, de a "
                    "készletállapotot nem sikerült "
                    "egyértelműen meghatározni."
                )

            print(
                f"Aktuális készletállapot: {stock_text}"
            )

            if stock_text == "Készleten":
                in_stock = True

        finally:
            browser.close()

    if in_stock:
        print(
            "!!! iPhone 16e 128 GB KÉSZLETEN !!!"
        )
        send_email()

    else:
        print(
            "iPhone 16e 128 GB jelenleg nincs készleten. "
            "E-mail nem ment ki."
        )


if __name__ == "__main__":
    main()
