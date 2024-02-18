import json
import os
import re
import time
from pathlib import Path

import requests
from beartype import beartype
from beartype.typing import Any, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from gitlab.v4.objects import Group, Issue, Project, ProjectIssueNote

# Regex pattern to match strings starting with 'uploads/'
FILE_UPLOAD_PATTERN = r"uploads\/[a-zA-Z0-9\/_.-]+"


@beartype
def download_file_from_url(
    server: str, username: str, password: str, file_urls: List[str], download_dir: str = ""
) -> None:
    """Downloads files from given URLs using Selenium and ChromeDriver, after logging in with provided credentials.

    Args:
        server (str): The base URL of the server where the files are hosted.
        username (str): The username for login.
        password (str): The password for login.
        attachment_urls (List[str]): A list of URLs (relative to the server base URL) for the attachments to download.
        download_dir (str, optional): The directory where files should be downloaded. Defaults to the current directory.
    """
    chrome_options = Options()
    if download_dir:
        # Ensure the download directory exists
        download_dir = Path(download_dir).resolve()
        download_dir.mkdir(parents=True, exist_ok=True)
        # Set Chrome preferences for downloads
        chrome_prefs = {
            "download.default_directory": str(download_dir),
            "download.prompt_for_download": False,  # Disable download prompt
            "download.directory_upgrade": True,  # Enable directory upgrade
            "safebrowsing_for_trusted_sources_enabled": False,  # Disable safe browsing for trusted sources
            "safebrowsing.enabled": False,  # Disable safe browsing
            "plugins.always_open_pdf_externally": True,  # Automatically download PDFs instead of opening them
        }
        chrome_options.add_experimental_option("prefs", chrome_prefs)

    # Initialize the Chrome WebDriver
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

    # Perform login
    login_url = f"{server}/users/sign_in"
    driver.get(login_url)
    time.sleep(2)  # Wait for the login page to load

    # Fill in the login credentials and submit
    driver.find_element(By.ID, "user_login").send_keys(username)
    time.sleep(1)
    driver.find_element(By.ID, "user_password").send_keys(password)
    time.sleep(1)
    driver.find_element(By.CLASS_NAME, "js-sign-in-button").click()
    time.sleep(3)  # Wait for login to complete

    # Download each file by navigating to its URL
    for file_url in file_urls:
        if file_url.endswith((".png", ".jpg", ".jpeg", ".gif", ".html")):
            selenium_cookies = driver.get_cookies()
            cookies = {cookie["name"]: cookie["value"] for cookie in selenium_cookies}

            local_filename = file_url.split("/")[-1]
            i = 0
            while (download_dir / local_filename).exists():
                i += 1
                local_filename = Path(local_filename).stem + f"_{i}" + Path(local_filename).suffix

            with requests.get(file_url, cookies=cookies, stream=True) as r:
                r.raise_for_status()
                with open(download_dir / local_filename, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

        else:
            driver.get(file_url)

        time.sleep(2)  # Wait for each file to start downloading

    # Placeholder for user to check downloads before quitting
    driver.quit()


@beartype
def find_matches(obj: None | str | list | dict[str, Any], pattern: str, found: List[str] = None) -> List[str]:
    """
    Recursively searches for all strings in a nested JSON-like object that match a given regex pattern.

    Args:
        obj (dict[str, Any]): The JSON-like object (dict, list, or str) to search through.
        pattern (str): The regex pattern to match strings against.
        found (List[str], optional): Accumulator for matches found during recursion. Defaults to None.

    Returns:
        List[str]: A list of all strings found in the object that match the regex pattern.
    """
    if found is None:
        found = []

    if isinstance(obj, dict):
        for value in obj.values():
            find_matches(value, pattern, found)

    elif isinstance(obj, list):
        for item in obj:
            find_matches(item, pattern, found)

    elif isinstance(obj, str):
        found += re.findall(pattern, obj)

    return found


@beartype
def get_wiki_attachment_urls(obj: Group | Project, pattern: str) -> List[str]:
    """Extracts attachment URLs from the "description" field of a GitLab wiki objects.

    Args:
        obj (Group | Project): The wiki object to extract attachment URLs from.
        pattern (str): The regex pattern to match strings against.

    Returns:
        List[str]: A list of attachment URLs extracted from the wiki contents.
    """

    pages = obj.wikis.list(all=True)
    matches = []
    for page in pages:
        content = obj.wikis.get(page.slug).content
        matches += find_matches(content, pattern)

    attachment_urls = []
    for attachment_uri in matches:
        if not attachment_uri:
            continue

        if "uploads/-" in attachment_uri:
            attachment_uri = attachment_uri.replace("uploads/-/", "-/wikis/uploads/")

        url = obj.web_url
        attachment_url = f"{url}/-/wikis/{attachment_uri}"
        attachment_urls.append(attachment_url)

    return attachment_urls


def get_issue_attachment_urls(
    obj: Issue | ProjectIssueNote, pattern: str, is_note=False, web_url: str = ""
) -> List[str]:
    """Extracts attachment URLs from the "description" field of a GitLab issue.

    Args:
        issue (dict[str, Any]): The issue json object to extract attachment URLs from.
        pattern (str): The regex pattern to match strings against.

    Returns:
        List[str]: A list of attachment URLs extracted from the issue description.
    """
    if is_note:
        matches = find_matches(obj.body, pattern)
    else:
        matches = find_matches(obj.description, pattern)

    attachment_urls = []
    for attachment_uri in matches:
        if "uploads/-" in attachment_uri:
            attachment_uri = attachment_uri.replace("uploads/-/", "uploads/")

        url = obj.web_url.split("/-/issues/")[0] if not is_note else web_url.split("/-/issues/")[0]
        attachment_url = f"{url}/{attachment_uri}"
        attachment_urls.append(attachment_url)

    return attachment_urls


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    # Your GitLab credentials and URL
    SERVER = os.getenv("GITLAB_SERVER")
    USERNAME = os.getenv("GITLAB_USERNAME")
    PASSWORD = os.getenv("GITLAB_PASSWORD")

    # Load the JSON data from a file
    with open("EXAMPLE_PATH_TO_ISSUE_JSON") as f:
        issue = json.load(f)

    # Assuming you have a function `download_file_from_url` defined elsewhere
    # from your_module import download_file_from_url
    attachment_urls = get_issue_attachment_urls(issue, FILE_UPLOAD_PATTERN)

    # Assuming `SERVER`, `USERNAME`, `PASSWORD`, and `download_dir` are defined
    download_file_from_url(SERVER, USERNAME, PASSWORD, attachment_urls, download_dir="./")
