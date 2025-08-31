import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio

# ------------------ CONFIG ------------------
MHADA_PAN = "BFBPJ6615K"   # PAN Number
MHADA_PASSWORD = "Kisan@9860"  # Portal Password
EMAIL_FROM = "sachinjundharecloud909@gmail.com"
EMAIL_FROM_APP_PASSWORD = "Cloud@7878"  # ⚠️ Use Gmail App Password
EMAIL_TO = "sachinjundhare909@gmail.com"
LOGIN_URL = "https://bookmyhome.mhada.gov.in/signIn"
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
    print("Opening login page...")
    # Add timeout and wait_until
    await page.goto(
        "https://bookmyhome.mhada.gov.in/signIn",
        timeout=50000,                     # wait up to 60s
        wait_until="domcontentloaded"      # stop waiting once DOM is ready
    )
    print("after login page opened...")
    await page.wait_for_timeout(5000)
    print("starting pan and password adding...")
    # Fill PAN and Password fields
    await page.fill("input.input-otp", MHADA_PAN)
    print("pan card added...")
    await page.fill("input[type='password']", MHADA_PASSWORD)
    print("password added...")
    
    # Click Login button
    await page.click("button[type='submit']")
    print("🔑 Submitted login form.")

    # Give time for navigation
    await page.wait_for_timeout(5000)

    # Navigate to Pune schemes
    try:
        await page.click("text=Pune", timeout=10000)
        await page.click("text=PB_01_01 FCFS 20 percent Schemes", timeout=10000)
    except TimeoutError:
        print("⚠️ Could not navigate to Pune/target scheme.")

    # Scrape page
    content = await page.content()
    return parse_scheme_list(content)


# ---- Main Scraper ----
async def run_checker():
    if async_playwright is None:
        print("⚠️ Playwright not available. Running in test mode.")
        test_mode()
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()

        try:
            new_list = await login_and_scrape(page)
        except Exception as e:
            print("⚠️ First login attempt failed, retrying once...", e)
            await page.close()
            page = await browser.new_page()
            new_list = await login_and_scrape(page)

        # Load old list
        try:
            with open("schemes_snapshot.txt", "r") as f:
                old_list = f.read().splitlines()
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


# ---- Test Mode (no Playwright) ----
def test_mode():
    old_list = ["PB_01_01 FCFS 20 percent Schemes - A"]
    new_html = """
    <div>PB_01_01 FCFS 20 percent Schemes - A</div>
    <div>PB_01_01 FCFS 20 percent Schemes - B</div>
    """
    new_list = parse_scheme_list(new_html)
    new_items = detect_new_items(old_list, new_list)
    assert new_items == ["PB_01_01 FCFS 20 percent Schemes - B"]
    print("✅ Test mode passed. Detected new:", new_items)


if __name__ == "__main__":
    asyncio.run(run_checker())
