import time
import requests
from bs4 import BeautifulSoup
from stem import Signal
from stem.control import Controller

VENDORS_WHITELIST = ['samsung', 'xiaomi', 'tecno', 'infinix', 'huawei', 'realme', 'blackview', 'itel']

# Tor proxy and control port config
SOCKS_PROXY = "socks5h://127.0.0.1:9050"
CONTROL_PORT = 9051
CONTROL_PASSWORD = "my_password"

# So that they won't block us in case we don't look legit
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
}

# Here they have a table with all vendors
BASE_URL = "https://www.gsmarena.com/"
MAKERS_URL = BASE_URL + "makers.php3"

# I want all the traffic to go through TOR
proxies = {
    "http": SOCKS_PROXY,
    "https": SOCKS_PROXY,
}

# Change my IP
def renew_tor_identity():
    print("Requesting new Tor identity")
    with Controller.from_port(port=CONTROL_PORT) as controller:
        controller.authenticate(password=CONTROL_PASSWORD)

        # Signal request for renewal of identity
        controller.signal(Signal.NEWNYM)
    print("New identity requested, waiting 10 seconds")
    time.sleep(10)  # Give Tor time to switch circuits

def fetch_url(url, max_retries=10):
    for attempt in range(max_retries):
        try:
            print(f"Fetching {url} (Attempt {attempt})")
            response = requests.get(url, headers=HEADERS, proxies=proxies, timeout=15)
            if response.status_code == 429: # Too MAny Requests
                print(f"429 Rate limited on attempt {attempt}. Renewing identity")
                renew_tor_identity()
                continue
            response.raise_for_status() # If any other error it will raise exception
            time.sleep(1.5) # random I chose for safety so that I won't get blocked frequently
            return response.text
        except requests.RequestException as e:
            print(f"Request failed: {e}. Renewing identity and retrying")
            renew_tor_identity()
    raise Exception(f"Failed to fetch {url} after {max_retries} attempts")

def parse_makers(html):
    soup = BeautifulSoup(html, "html.parser")
    makers_div = soup.find("div", {"class": "st-text"})
    makers = []
    if makers_div:
        for a in makers_div.find_all("a"):
            name = a.text.strip()
            href = a.get("href")
            if href:
                makers.append((name, BASE_URL + href))
    return makers

def parse_models(html):
    soup = BeautifulSoup(html, "html.parser")
    models = []
    makers_div = soup.find("div", {"class": "makers"})
    if makers_div:
        for li in makers_div.find_all("li"):
            a = li.find("a")
            if a:
                model_name = a.find("strong").text.strip() if a.find("strong") else a.text.strip() # Thats where they store the name
                model_link = BASE_URL + a.get("href")
                models.append((model_name, model_link))
    return models

def parse_esim(html):
    soup = BeautifulSoup(html, "html.parser")
    # Check if "eSIM" appears anywhere in the page
    return "esim" in soup.text.lower()

def main():
    html_makers_table = fetch_url(MAKERS_URL)
    makers = parse_makers(html_makers_table)
    print(f"Found {len(makers)} makers:")
    for name, link in makers:
        if any(sub in name.lower() for sub in VENDORS_WHITELIST):
            print(f"- {name}: {link}")
            html_maker = fetch_url(link)
            models = parse_models(html_maker)
            for model_name, model_link in models:
                if parse_esim(fetch_url(model_link)):
                    print(f"-- {model_name} is supporting eSim - {model_link}")



if __name__ == "__main__":
    main()
