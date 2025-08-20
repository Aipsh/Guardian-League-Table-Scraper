import sys
import subprocess
import importlib
import re
import os
import datetime
from urllib.parse import urlparse

import tkinter as tk
from tkinter import filedialog

# Check packages are installed
def ensure_package(pip_name, import_name=None):
    import_name = import_name or pip_name
    try:
        importlib.import_module(import_name)
    except ImportError:
        print(f"Package '{pip_name}' not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
    finally:
        globals()[import_name] = importlib.import_module(import_name)

packages = [
    ("requests", "requests"),
    ("pandas", "pandas"),
    ("beautifulsoup4", "bs4"),
]

for pip_name, import_name in packages:
    ensure_package(pip_name, import_name)

import requests
import pandas
from bs4 import BeautifulSoup

# HTTP stuff
TIMEOUT = 25
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def http_get_text(url):
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text

def http_get_json(url):
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()

# REGEX for the URL
# overview.json
JSON_URL_RE = re.compile(
    r"https://interactive\.guim\.co\.uk/atoms/labs/\d{4}/\d{2}/university-guide/(?:overview/)?v/\d+/assets/data/overview\.json"
)

# app.js in either style
APPJS_URL_RE = re.compile(
    r"https://interactive\.guim\.co\.uk/atoms/labs/\d{4}/\d{2}/university-guide/(?:overview/)?v/\d+/app\.js"
)

# base path to build overview.json if needed
BASE_PATH_RE = re.compile(
    r"(https://interactive\.guim\.co\.uk/atoms/labs/\d{4}/\d{2}/university-guide/(?:overview/)?v/\d+/)"
)

# Extract year from URL
def extract_year_from_url(url):
    """
       Extract first 4-digit year from the URL and return +1 as string.
       E.g. 2020 → '2021'
       """
    m = re.search(r"/(\d{4})/", url)
    if m:
        return str(int(m.group(1)) + 1)
    else:
        raise ValueError(f"No 4-digit year found in URL: {url}")

# Get JSON URL from appjs
def extract_json_url_from_appjs(appjs_url):
    print(f"Fetching app.js from {appjs_url}")
    text = http_get_text(appjs_url)
    match = JSON_URL_RE.search(text)
    if not match:
        raise Exception("Could not find overview.json URL in app.js")
    return match.group(0)

def get_appjs_url_from_page(page_url):
    """
    Updated: now checks <script src="..."> and inline scripts for app.js,
    with /overview/ optional in the path.
    """
    print(f"Fetching page from {page_url}")
    html = http_get_text(page_url)
    soup = BeautifulSoup(html, "html.parser")

    # 1) Look for <script src="...app.js">
    for script in soup.find_all("script", src=True):
        src = script["src"]
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = "https://www.theguardian.com" + src
        m = APPJS_URL_RE.search(src)
        if m:
            return m.group(0)

    # 2) Look for inline references
    for script in soup.find_all("script"):
        s = script.string or script.text or ""
        m = APPJS_URL_RE.search(s)
        if m:
            return m.group(0)

    raise Exception("Could not find app.js URL on page")

def discover_overview_json_url(page_url):
    #1) Try to find overview.json directly in page HTML
    #2) Fallback to app.js → extract JSON
    #3) Fallback to constructing from base interactive path if present

    print(f"Discovering overview.json from: {page_url}")
    html = http_get_text(page_url)

    # 1) JSON directly in HTML
    m = JSON_URL_RE.search(html)
    if m:
        print("Found overview.json directly in page HTML.")
        return m.group(0)

    # 2) app.js path in HTML (src or inline)
    print("overview.json not in HTML. Looking for app.js...")
    soup = BeautifulSoup(html, "html.parser")

    # 2a) src attribute
    for script in soup.find_all("script", src=True):
        src = script["src"]
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = "https://www.theguardian.com" + src
        m = APPJS_URL_RE.search(src)
        if m:
            return extract_json_url_from_appjs(m.group(0))

    # 2b) inline
    for script in soup.find_all("script"):
        s = script.string or script.text or ""
        m = APPJS_URL_RE.search(s)
        if m:
            return extract_json_url_from_appjs(m.group(0))

    # 3) Construct from base path if visible anywhere
    print("app.js not found. Trying to construct overview.json from a base path...")
    m = BASE_PATH_RE.search(html)
    if m:
        base = m.group(1)  # ends with .../v/<digits>/
        candidate = base + "assets/data/overview.json"
        try:
            # Validate it exists
            _ = http_get_text(candidate)
            print("Constructed overview.json URL is valid.")
            return candidate
        except Exception:
            pass

    raise Exception("Could not find app.js or overview.json URL on page")

# Filepath stuff
def generate_output_folder(base_dir, year):
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%b-%d")
    time_str = now.strftime("%H%M")
    folder_name = f"gug_{year}.at {today_str}_{time_str}"
    full_path = os.path.join(base_dir, folder_name)
    os.makedirs(full_path, exist_ok=True)
    return full_path

def save_subjects_csv(data, output_dir):
    if "subjects" in data:
        df = pandas.DataFrame(data["subjects"])
        df.to_csv(os.path.join(output_dir, "subjects.csv"), index=False)
        print("Saved subjects.csv")
        return df
    else:
        raise Exception("No 'subjects' key found in JSON")

def download_subjects_data(base_prefix, subjects_df, output_dir, year_label):
    #Asks for a search string (case-insensitive).
    #If search = 'all' or blank, save everything.
    #Otherwise, save only if second column contains the search string (exactly).
    #Append search value (the subject) to CSV filenames.
    #Makes a csv (summary subjects) that shows which subjects the university name is present in.

    raw_input = input("\nEnter the institution name to search for in subject tables. It will only save a subject if the name appears.\nThe institution name must match how The Guardian defines it!\nOR leave blank to save everything:\n").strip()

    search_value = raw_input.lower()
    save_all = (search_value == "" or search_value == "all")

    suffix = search_value if not save_all else "all"

    found_subjects = []
    not_found_subjects = []

    for _, row in subjects_df.iterrows():
        subject_id = str(row["id"]).strip()
        subject_title = str(row["title"]).strip()

        subject_json_url = f"{base_prefix}/{subject_id}.json"
        print(f"\n🛜 Downloading JSON for subject '{subject_title}' from:\n{subject_json_url}")

        try:
            subj_data = http_get_json(subject_json_url)
        except Exception as e:
            print(f"Error fetching subject JSON for '{subject_title}': {e}")
            not_found_subjects.append(subject_title)
            continue

        if "institutions" not in subj_data:
            print(f"Warning: No 'institutions' key in JSON for '{subject_title}' ({subject_json_url})")
            not_found_subjects.append(subject_title)
            continue

        df = pandas.DataFrame(subj_data["institutions"])

        has_value = False
        if save_all:
            has_value = True
        elif df.shape[1] >= 2:
            second_col = df.iloc[:, 1].astype(str).str.lower().str.strip()
            # Check for exact match only
            if (second_col == search_value).any():
                has_value = True

        safe_name = re.sub(r'[\\/*?:"<>|]', "_", subject_title)
        csv_filename = f"{safe_name}_{year_label}_{suffix}.csv"
        csv_path = os.path.join(output_dir, csv_filename)

        if has_value:
            found_subjects.append(subject_title)
            try:
                df.to_csv(csv_path, index=False)
                print(f"💾 Saved {csv_filename}")
            except Exception as e:
                print(f"Error saving {csv_filename}: {e}")
                not_found_subjects.append(subject_title)
        else:
            not_found_subjects.append(subject_title)
            print(f"🙂‍↔️ Skipping save for '{subject_title}': '{search_value}' not found in second column.")

    # Balance lists for clean summary
    max_len = max(len(found_subjects), len(not_found_subjects))
    found_subjects += [""] * (max_len - len(found_subjects))
    not_found_subjects += [""] * (max_len - len(not_found_subjects))

    summary_df = pandas.DataFrame({
        f"Subjects with '{suffix}'": found_subjects,
        f"Subjects without '{suffix}'": not_found_subjects
    })
    summary_csv_path = os.path.join(output_dir, f"subjects_summary_{year_label}_{suffix}.csv")
    summary_df.to_csv(summary_csv_path, index=False)
    print(f"\n👍 Saved subjects summary to: {summary_csv_path}")

    # Print list of saved subjects
    if found_subjects:
        print("\n🙌 Subjects saved:")
        for subj in found_subjects:
            if subj:
                print(f" ️💾 - {subj}")

    # Print list of skipped subjects
    if not_found_subjects:
        print("\n🫸 Subjects skipped:")
        for subj in not_found_subjects:
            if subj:
                print(f" 🙂‍↔️ - {subj}")


# Run scrapes
def run_year_data(page_url, base_dir, year_label=None):
    if not year_label:
        year_label = extract_year_from_url(page_url)  # <- use URL year if not provided

    output_dir = generate_output_folder(base_dir, year_label)

    # unified discovery (handles 2023 & 2025 styles)
    overview_json_url = discover_overview_json_url(page_url)

    # download overview and write CSVs
    overview_data = http_get_json(overview_json_url)
    subjects_df = save_subjects_csv(overview_data, output_dir)

    if "institutions" in overview_data:
        overall_path = os.path.join(output_dir, "Overall.csv")
        pandas.DataFrame(overview_data["institutions"]).to_csv(overall_path, index=False)
        print("Saved Overall.csv")

    base_prefix = overview_json_url.rsplit('/', 1)[0]
    download_subjects_data(base_prefix, subjects_df, output_dir, year_label)

    print(f"\n👍 Data for {year_label} saved in {output_dir}\n")

# Main
def main():
    root = tk.Tk()
    root.withdraw()

    print("Please select the folder where output should be saved.")
    base_dir = filedialog.askdirectory(title="Select folder to save output")
    if not base_dir:
        print("No folder selected, exiting.")
        return

    # CURRENT year data
    current_url = input("\nEnter the first Guardian university rankings page URL: \ne.g. \nhttps://www.theguardian.com/education/ng-interactive/2024/sep/07/the-guardian-university-guide-2025-the-rankings \nPaste URL and hit enter:\n").strip()
    run_year_data(current_url, base_dir)

    # PREVIOUS year data
    previous_url = input("\nEnter the second Guardian university rankings page URL: \ne.g. \nhttps://www.theguardian.com/education/ng-interactive/2023/sep/09/the-guardian-university-guide-2024-the-rankings \nPaste URL and hit enter:\n").strip()
    run_year_data(previous_url, base_dir)

if __name__ == "__main__":
    main()
