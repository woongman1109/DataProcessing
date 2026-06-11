# 📄 HTML 파일 경로 (수정 가능)
html_path = r"C:\Users\woong\Dropbox\==== SKKU-SAINT ====\==== SAINT-OSL ====\2. Measurements\0. Data Processing\RefManager\Kangs Group Publications.html"

import os
from bs4 import BeautifulSoup
import requests
import re
import pandas as pd
from urllib.parse import unquote


# HTML 파싱
with open(html_path, 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'html.parser')

# 유효 링크 필터링
valid_domains = [
    'doi.org', 'pubs.acs.org', 'onlinelibrary.wiley.com', 'sciencedirect.com',
    'rsc.org', 'nature.com', 'springer.com', 'mdpi.com', 'ieee.org'
]

paper_links = []
for a in soup.find_all('a', href=True):
    href = unquote(a['href'])
    if any(domain in href for domain in valid_domains):
        paper_links.append(href)

unique_links = sorted(set(paper_links))

# 📄 정보 추출
headers = {"User-Agent": "Mozilla/5.0"}
funding_pattern = re.compile(r"(NRF[-\d]+|RS[-\dNR]+|과제\s*번호[:：]?\s*\d{6,})", re.IGNORECASE)

results = []

for link in unique_links:
    try:
        res = requests.get(link, headers=headers, timeout=20)
        if res.status_code != 200:
            continue

        soup = BeautifulSoup(res.text, "html.parser")
        title = soup.title.string.strip() if soup.title else ""

        year_match = re.search(r"\b(20\d{2})\b", res.text)
        year = year_match.group(1) if year_match else ""

        meta_journal = soup.find("meta", {"name": "citation_journal_title"})
        journal = meta_journal["content"] if meta_journal else ""

        ack_texts = soup.find_all(string=re.compile(r"acknowledg|funding|grants?", re.IGNORECASE))
        ack_combined = " ".join(ack_texts)
        sasa = funding_pattern.findall(ack_combined) or ["미상"]

        for grant in sasa:
            results.append({
                "link": link,
                "title": title,
                "year": year,
                "journal": journal,
                "funding": grant,
            })
    except Exception as e:
        results.append({
            "link": link,
            "title": f"오류: {str(e)}",
            "year": "",
            "journal": "",
            "funding": "",
        })

# 📊 DataFrame 생성 및 확인
df = pd.DataFrame(results)

# 🖨 출력 (선택)
print(df.head(10))

# 💾 엑셀 저장
df.to_excel("논문_정보_요약.xlsx", index=False)
print("✅ 저장 완료: 논문_정보_요약.xlsx")
