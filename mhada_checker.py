import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio

# ------------------ CONFIG ------------------
MHADA_PAN = "BFBPJ6615K"   # PAN Number
MHADA_PASSWORD = "Kisan@9860"  # Portal Password
EMAIL_FROM = "sachinjundharecloud909@gmail.com"
EMAIL_FROM_APP_PASSWORD = "spdj nenh cyhb svbm"  # ⚠️ Use Gmail App Password
EMAIL_TO = "sachinjundhare909@gmail.com"
LOGIN_URL = "https://bookmyhome.mhada.gov.in/"
# --------------------------------------------

try:
    from playwright.async_api import async_playwright, TimeoutError
except ImportError:
    async_playwright = None


# ---- Email function ----
def send_email_alert(new_items):
    subject = "MHADA Alert: New Flats Detected"
    body = "New flats/schemes have been added:\n" + "\n".join(new_items)

    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_FROM_APP_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        print("✅ Email sent successfully!")
    except Exception as e:
        print("❌ Email failed:", e)


# ---- Parse scheme list ----
def parse_scheme_list(page_content):
    # Example: match scheme names from HTML
    return re.findall(r"PB_01_01[^<]+", page_content)


# ---- Diff check ----
def detect_new_items(old_list, new_list):
    return [item for item in new_list if item not in old_list]


# ---- Login & Scrape ----
async def login_and_scrape(page):
    print("Opening home page...")
    # Add timeout and wait_until
    await page.goto(
        "https://bookmyhome.mhada.gov.in/",
        timeout=50000,                     # wait up to 60s
        wait_until="domcontentloaded"      # stop waiting once DOM is ready
    )
    print("after home page opened...")
    await page.wait_for_timeout(5000)
    await page.click("xpath=/html/body/app-root/ion-app/div/ion-content/app-landing/div/div[2]/div[3]/div/button[1]")
    print("signup form opened.")
    await page.wait_for_timeout(5000)
    await page.click("xpath=/html/body/app-root/ion-app/div/ion-content/app-signup/div/div[2]/div/div[3]/a")
    print("login form opened.")
    
    print("starting pan and password adding...")
    # Fill PAN and Password fields
    await page.wait_for_selector("xpath=/html/body/app-root/ion-app/div/ion-content/app-login/div/div[2]/div/div[3]/div[1]/div[2]/input", timeout=5000)
    await page.fill("xpath=/html/body/app-root/ion-app/div/ion-content/app-login/div/div[2]/div/div[3]/div[1]/div[2]/input", MHADA_PAN)

    print("pan card added...")
    
    await page.wait_for_selector("xpath=/html/body/app-root/ion-app/div/ion-content/app-login/div/div[2]/div/div[3]/div[2]/div[2]/input", timeout=5000)
    await page.fill("xpath=/html/body/app-root/ion-app/div/ion-content/app-login/div/div[2]/div/div[3]/div[2]/div[2]/input", MHADA_PASSWORD)
    
    print("password added...")
    await page.wait_for_timeout(5000)
    # Click Login button
    await page.click("xpath=/html/body/app-root/ion-app/div/ion-content/app-login/div/div[2]/div/div[3]/div[4]/div[1]/button")
    print("Submitted login form.")
    
    # Give time for navigation
    await page.wait_for_timeout(5000)
    print("profile form start")
    
    # profile
    await page.click("xpath=/html/body/app-root/ion-app/div/ion-content/app-profile-new/div/div[2]/button[2]")
    print("clicked on apply..")
    await page.wait_for_timeout(5000)
    
    # Navigate to Pune schemes
    await page.click("xpath=/html/body/app-root/ion-app/div/ion-content/app-select-board/div/div[2]/div/div[2]/div/div/p")
    print("Pune schemes opened")
    await page.wait_for_timeout(5000)

    print("opening PB_01_01 - FCFS 20 percent Schemes")
    await page.click("xpath=/html/body/app-root/ion-app/div/ion-content/app-select-lottery/div/div/div/div/div/div/div[1]/div/div[1]/button[2]/span")
    print("percent scheme opened")
    await page.wait_for_timeout(10000)

    buttons = await page.query_selector_all("span.text-white")
    print("Total SELECT LOCATION buttons:", len(buttons))

    # Scrape page
    content = await page.content()
    return parse_scheme_list(content)


# ---- Main Scraper ----
async def run_checker():
    if async_playwright is None:
        print("Playwright not available..")
        return
    print("Starting script..")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        print("Chrome opened..")
        try:
            new_list = await login_and_scrape(page)
            print("New list:", new_list)
        except Exception as e:
            print("First login attempt failed, retrying once...", e)
            await page.close()
            page = await browser.new_page()
            new_list = await login_and_scrape(page)

        # Load old list
        try:
            with open("schemes_snapshot.txt", "r") as f:
                old_list = f.read().splitlines()
                print("Old list:", old_list)
        except FileNotFoundError:
            old_list = []

        # Detect changes
        new_items = detect_new_items(old_list, new_list)
        if new_items:
            send_email_alert(new_items)

        # Save snapshot
        with open("schemes_snapshot.txt", "w") as f:
            f.write("\n".join(new_list))

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run_checker())
