import requests
from bs4 import BeautifulSoup
import json
import re


def ExtractContent(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    content_lines = []

    # Remove irrelevant sections
    for tag in soup(["script", "style", "footer", "nav"]):
        tag.decompose()

    for tag in soup.find_all(class_="prev-next-area"):
        tag.decompose()

    # Extract relevant HTML content
    for tag in soup.body.descendants:
        if tag.name:
            if tag.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                level = int(tag.name[1])
                content_lines.append(f"{'#' * level} {tag.get_text(strip=True)}\n")

            elif tag.name == "dt":
                text = tag.get_text(strip=False)
                content_lines.append(f"`{text}`")

            elif tag.name == "p":
                text = tag.get_text(separator=" ", strip=True)
                if text:
                    corrected_text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
                    content_lines.append(f"{corrected_text}\n")

            elif tag.name == "pre":
                code_text = tag.get_text()
                content_lines.append(f"```\n{code_text}\n```\n")

            elif tag.name == "table":
                rows = tag.find_all("tr")
                table_data = []
                for row in rows:
                    cols = [col.get_text(strip=True) for col in row.find_all(["th", "td"])]
                    if cols:
                        table_data.append(cols)
                if table_data:
                    headers = table_data[0]
                    content_lines.append("| " + " | ".join(headers) + " |")
                    content_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                    for row in table_data[1:]:
                        content_lines.append("| " + " | ".join(row) + " |")
                    content_lines.append("")

    # Clean and return structured text
    doc_text = "\n".join(content_lines).strip()
    doc_text = doc_text.replace("Â", "").replace("¶", "")

    return {
        "url": url,
        "content": doc_text
    }

if __name__ == "__main__":
    urls = [
        "https://docs.snowflake.com/en/sql-reference/constraints",
        "https://docs.snowflake.com/en/sql-reference/constraints-overview",
        "https://docs.snowflake.com/en/sql-reference/constraints-create",
        "https://docs.snowflake.com/en/sql-reference/constraints-alter",
        "https://docs.snowflake.com/en/sql-reference/constraints-drop",
    ]

    results = []
    for url in urls:
        print(f"Extracting content from: {url}")
        try:
            data = ExtractContent(url)
            results.append(data)
        except Exception as e:
            print(f"Error processing {url}: {e}")

    output_file = "snowflake_docs_extracted.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print(f"\n Extraction complete. Output saved to: {output_file}")
