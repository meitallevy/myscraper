import time
import csv
import requests
from bs4 import BeautifulSoup
from stem import Signal
from stem.control import Controller

# Whitelist of specific vendors we're interested in
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

BASE_URL = "https://www.gsmarena.com/"

# Here they have a table with all vendors
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
    time.sleep(10)

def fetch_url(url, max_retries=10):
    for attempt in range(max_retries):
        try:
            print(f"Fetching {url} (Attempt {attempt})")
            response = requests.get(url, headers=HEADERS, proxies=proxies, timeout=15)
            if response.status_code == 429:  # Too Many Requests
                print(f"429 Rate limited on attempt {attempt}. Renewing identity")
                renew_tor_identity()
                continue
            response.raise_for_status()  # If any other error it will raise exception
            time.sleep(1.5)  # random I chose for safety so that I won't get blocked frequently
            return response.text
        except requests.RequestException as e:
            print(f"Request failed: {e}. Renewing identity and retrying")
            renew_tor_identity()
    raise Exception(f"Failed to fetch {url} after {max_retries} attempts")

def parse_makers(html):
    soup = BeautifulSoup(html, "html.parser")
    makers_div = soup.find("div",                                                                                                                                                                                                                                                                                                                                                                                                                                                                   {"class": "st-text"})
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
                model_name = a.find("strong").text.strip() if a.find("strong") else a.text.strip()
                model_link = BASE_URL + a.get("href")
                models.append((model_name, model_link))
    return models

def parse_params(html, specific_params=None):
    params_dict ={}
    soup = BeautifulSoup(html, "html.parser")
    specs_table = soup.find('div', {"id": "specs-list"})
    if specs_table:
        trs = specs_table.find_all("tr")
        for tr in trs:
            if tr:
                spec_tag = tr.find("td", {"class":"ttl"})
                if spec_tag:
                    spec = spec_tag.find("a")
                    if spec:
                        if (not specific_params) or spec.contents in specific_params:
                            params_dict[str(spec)] = str(tr.find("td", {"class":"nfo"}).contents)
    return params_dict

def parse_esim(html):
    soup = BeautifulSoup(html, "html.parser")
    sim_td = soup.find("td", {"data-spec": "sim", "class":"nfo"})
    if sim_td:
        return "esim" in sim_td.text.lower(), sim_td.contents
    return False, None

def main():
    html_makers_table = fetch_url(MAKERS_URL)
    makers = parse_makers(html_makers_table)

    # Open CSV for writing model data with headers
    with open("gsmarena_models.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        # Write header row to CSV
        writer.writerow(["maker", "maker_link", "model_name", "model_link", "esim_support","sim_data", "source"])

        print(f"Found {len(makers)} makers:")
        for maker_name, maker_link in makers:
            if any(sub in maker_name.lower() for sub in VENDORS_WHITELIST):
                print(f"- {maker_name}: {maker_link}")
                html_maker = fetch_url(maker_link)
                models = parse_models(html_maker)
                for model_name, model_link in models:
                    html_model = fetch_url(model_link)
                    esim_support, sim_data = parse_esim(html_model)
                    params = parse_params(html_model)
                    print(f"-- {model_name} | eSIM: {esim_support}")

                    if esim_support:
                        writer.writerow([
                            maker_name,
                            maker_link,
                            model_name,
                            model_link,
                            esim_support,
                            sim_data,
                            "GSMARENA",  # Hardcoded source column
                            params
                        ])

if __name__ == "__main__":
    main()
