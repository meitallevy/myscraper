import random
import time
import requests
import sqlite3
import uuid
from bs4 import BeautifulSoup
from stem import Signal
from stem.control import Controller

# Whitelist of specific vendors we're interested in
VENDORS_WHITELIST = ['samsung', 'xiaomi', 'tecno', 'infinix', 'huawei', 'realme', 'blackview', 'itel', 'google', 'honor', 'htc','nothing', 'oppo', 'oneplus', 'vivo', 'nokia', 'sony','lg']
# VENDORS_WHITELIST = list('abcdefghijklmnopqrstuvwxyz')

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

BASE_URL = "https://www.gsmarena.com/"

# Here they have a table with all vendors
MAKERS_URL = BASE_URL + "makers.php3"

# I want all the traffic to go through TOR
proxies = {
    "http": SOCKS_PROXY,
    "https": SOCKS_PROXY,
}

# SQLite DB setup (creates a file named gsmarena.db)
conn = sqlite3.connect("gsmarena.db")
c = conn.cursor()

# Create main table for models
c.execute("""
CREATE TABLE IF NOT EXISTS models_view (
    unique_model_id TEXT PRIMARY KEY,
    maker TEXT,
    maker_link TEXT,
    model_name TEXT,
    model_link TEXT,
    esim_support INTEGER,
    sim_data TEXT,
    is_android INTEGER,
    os_data TEXT
)
""")

# Create separate table for parameters
c.execute("""
CREATE TABLE IF NOT EXISTS models_params (
    unique_model_id TEXT,
    maker TEXT,
    model_name TEXT,
    param_name TEXT,
    param_value TEXT,
    FOREIGN KEY (unique_model_id) REFERENCES models_view(unique_model_id)
)
""")
conn.commit()


# Change my IP
def renew_tor_identity():
    print("Requesting new Tor identity")
    with Controller.from_port(port=CONTROL_PORT) as controller:
        controller.authenticate(password=CONTROL_PASSWORD)

        # Signal request for renewal of identity
        controller.signal(Signal.NEWNYM)
    print("New identity requested, waiting 15 seconds")
    time.sleep(15)


def fetch_url(url, max_retries=50):
    for attempt in range(max_retries):
        try:
            print(f"Fetching {url} (Attempt {attempt})")
            response = requests.get(url, headers=HEADERS, proxies=proxies, timeout=15)
            if response.status_code == 429:  # Too Many Requests
                print(f"429 Rate limited on attempt {attempt}. Renewing identity")
                renew_tor_identity()
                continue
            response.raise_for_status()  # If any other error it will raise exception
            time.sleep(random.randint(7,15))  # random I chose for safety so that I won't get blocked frequently
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
            span = a.find("span")
            if span:
                span.extract()
            name = a.text.strip().replace('\n', '')
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
                model_name = a.find("strong").text.strip() if a.find("strong") else a.text.strip()
                model_link = BASE_URL + a.get("href")
                models.append((model_name, model_link))
            else:
                print("no a tag in" + makers_div.text)
    else:
        print("no makers div in" + soup.text)
    return models


def parse_params(html, specific_params=None):
    params_dict = {}
    soup = BeautifulSoup(html, "html.parser")
    specs_table = soup.find('div', {"id": "specs-list"})

    if specs_table:
        trs = specs_table.find_all("tr")
        for tr in trs:
            value_tag = tr.find("td", {"class": "nfo"})
            if value_tag:
                spec_name = value_tag.get('data-spec')
                value = value_tag.get_text(separator=" ", strip=True)
                if (not specific_params) or (spec_name in specific_params):
                    params_dict[spec_name] = value
            else:
                print(tr.text + " is missing ttl and nfo")

    return params_dict


def parse_esim(html):
    soup = BeautifulSoup(html, "html.parser")
    sim_td = soup.find("td", {"data-spec": "sim", "class": "nfo"})
    if sim_td:
        return "esim" in sim_td.text.lower(), sim_td.text.strip()
    return False, None


def parse_os(html):
    soup = BeautifulSoup(html, "html.parser")
    os_td = soup.find("td", {"data-spec": "os", "class": "nfo"})
    if os_td:
        return "android" in os_td.text.lower(), os_td.text.strip()
    return False, None


def main():
    html_makers_table = fetch_url(MAKERS_URL)
    makers = parse_makers(html_makers_table)

    print(f"Found {len(makers)} makers:")
    for maker_name, maker_link in makers:
        if any(sub in maker_name.lower() for sub in VENDORS_WHITELIST):
            print(f"- {maker_name}: {maker_link}")
            page_number = 1
            while True:
                if page_number == 1:
                    url = maker_link
                else:
                    try:
                        base = maker_link.split("-phones-")[0]
                        vendor_id = maker_link.split("-phones-")[1].split(".php")[0]
                        url = f"{base}-phones-f-{vendor_id}-0-p{page_number}.php"
                    except Exception as e:
                        print(f"Error parsing pagination link: {e}")
                        break

                try:
                    html_maker = fetch_url(url)
                except Exception as e:
                    print(f"Failed to fetch {url}: {e}")
                    break

                models = parse_models(html_maker)
                if not models:
                    print(f"  No models found on page {page_number}, stopping.")
                    break

                print(f"  Page {page_number}: Found {len(models)} models")
                for model_name, model_link in models:
                    try:
                        html_model = fetch_url(model_link)
                        esim_support, sim_data = parse_esim(html_model)
                        is_android, os_data = parse_os(html_model)
                        params = parse_params(html_model)
                        print(f"    -- {model_name} | os: {os_data}")

                        # Generate a unique ID for this model
                        unique_model_id = str(uuid.uuid4())

                        # Save to models_view table
                        c.execute("""
                            INSERT INTO models_view (
                                unique_model_id, maker, maker_link,
                                model_name, model_link, esim_support, sim_data,
                                is_android, os_data
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            unique_model_id, maker_name, maker_link,
                            model_name, model_link, int(esim_support), sim_data, int(is_android), os_data
                        ))

                        # Save parameters to models_params table
                        for param_name, param_value in params.items():
                            c.execute("""
                                INSERT INTO models_params (
                                    unique_model_id, maker, model_name,
                                    param_name, param_value
                                ) VALUES (?, ?, ?, ?, ?)
                            """, (
                                unique_model_id, maker_name, model_name,
                                param_name, param_value
                            ))

                        # Commit after each model to save progress
                        conn.commit()
                    except Exception as e:
                        print(f"    Error processing {model_link}: {e}")
                        continue

                page_number += 1

if __name__ == "__main__":
    main()
