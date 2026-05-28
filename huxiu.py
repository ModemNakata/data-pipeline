import requests
from bs4 import BeautifulSoup

url = "https://www.huxiu.com/article/4862493.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

resp = requests.get(url, headers=headers, timeout=15)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "lxml")
text = soup.get_text(separator="\n", strip=True)
print(text)
