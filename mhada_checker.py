import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ------------------ CONFIG ------------------
MHADA_USERNAME = "BFBPJ6615K"
MHADA_PASSWORD = "Kisan@9860"
EMAIL_FROM = "sachinjundharecloud909@gmail.com"
EMAIL_FROM_APP_PASSWORD = "Cloud@7878"
EMAIL_TO = "sachinjundhare909@gmail.com"
LOGIN_URL = "https://bookmyhome.mhada.gov.in/signIn"
# --------------------------------------------

# Try importing Playwright (only available locally, not in this sandbox)
try:
    from playwright.async_api import async_playwright
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

# ---- Main Scraper ----
async def run_checker():
    if async_playwright is None:
        print("⚠️ Playwright not available. Running in test mode.")
        test_mode()
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 1. Login
        await page.goto(LOGIN_URL)
        await page.fill("input[name='username']", MHADA_USERNAME)
        await page.fill("input[name='password']", MHADA_PASSWORD)
        await page.click("button[type='submit']")

        # 2. Navigate (adjust selectors as per site)
        await page.click("text=Apply")
        await page.click("text=Pune")
        await page.click("text=PB_01_01 FCFS 20 percent Schemes")
        await page.click("text=Apply")

        # 3. Scrape scheme list
        content = await page.content()
        new_list = parse_scheme_list(content)

        # 4. Load old list from file
        try:
            with open("schemes_snapshot.txt", "r") as f:
                old_list = f.read().splitlines()
        except FileNotFoundError:
            old_list = []

        # 5. Detect changes
        new_items = detect_new_items(old_list, new_list)
        if new_items:
            send_email_alert(new_items)

        # 6. Save snapshot
        with open("schemes_snapshot.txt", "w") as f:
            f.write("\n".join(new_list))

        await browser.close()

# ---- Test Mode (no Playwright) ----
def test_mode():
    old_list = ["PB_01_01 FCFS 20 percent Schemes - A"]
    new_html = "<div>PB_01_01 FCFS 20 percent Schemes - A</div><div>PB_01_01 FCFS 20 percent Schemes - B</div>"
    new_list = parse_scheme_list(new_html)
    new_items = detect_new_items(old_list, new_list)
    assert new_items == ["PB_01_01 FCFS 20 percent Schemes - B"]
    print("✅ Test mode passed. Detected new:", new_items)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_checker())
