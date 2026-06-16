import os
import re
from pathlib import Path

# Define paths
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "data" / "raw_scraped"
DST_DIR = BASE_DIR / "data" / "netsol_scraped"

def clean_markdown_content(content: str) -> str:
    # 1. Remove header block (everything from start up to and including the Contact Us nav link)
    header_pattern = r"(?s)^.*?\[Contact Us\]\(https://netsoltech\.com/contact-us#contactUsForm\)\s*\n*"
    cleaned = re.sub(header_pattern, "", content, flags=re.IGNORECASE)
    
    # Fallback header pattern
    if len(cleaned) == len(content):
        cleaned = re.sub(r"(?s)^\s*\[\]\(https?://netsoltech\.com/?\)\s*\* Platform.*?\* \[Contact Us\]\(.*?\)\s*\n*", "", content, flags=re.IGNORECASE)

    # Careers header pattern (cleans up the navigation menu and Login/Register links)
    cleaned = re.sub(
        r"(?s)^\s*(\[\s*\]\(https?://careers\.netsoltech\.com/?\)\s*\n)?"
        r"(\s*\*?\s*\[\s*(Home|Vacancies|Why NETSOL|FAQs|Contact Us|Login|Register)\s*\]\(https?://careers\.netsoltech\.com/.*?\)\s*\n*)+",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    # 2. Truncate at common footers / noise markers
    markers = [
        r"##\s*Related blogs",
        r"##\s*Related Articles",
        r"##\s*Related Posts",
        r"#####\s*Subscribe to our newsletter"
    ]
    for marker in markers:
        parts = re.split(marker, cleaned, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) > 1:
            cleaned = parts[0]

    # Strip specific line headers that are noise
    cleaned = re.sub(r"###\s*Share this Blog:?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"###\s*Table of Contents\s*", "", cleaned, flags=re.IGNORECASE)

    # 3. Strip all image tags: ![alt](url)
    cleaned = re.sub(r"!\[.*?\]\(.*?\)", "", cleaned)

    # 4. Strip empty links: [](url)
    cleaned = re.sub(r"\[\]\(.*?\)", "", cleaned)

    # 5. Convert remaining markdown links [text](url) to plain text, preserving critical contact links
    def keep_or_strip_link(match):
        text = match.group(1)
        url = match.group(2)
        if any(keyword in url.lower() for keyword in ["mailto:", "tel:", "netsol"]):
            return f"[{text}]({url})"
        return text

    cleaned = re.sub(r"\[(.*?)\]\((.*?)\)", keep_or_strip_link, cleaned)

    # 6. Drop lines that are pure horizontal rules or other noise
    cleaned = re.sub(r"^[-*_]{3,}\s*$", "", cleaned, flags=re.MULTILINE)

    # 7. Clean up whitespace: replace 3 or more newlines with exactly 2
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()

def main():
    print(f"Source Directory: {SRC_DIR}")
    print(f"Destination Directory: {DST_DIR}")

    if not SRC_DIR.exists():
        print(f"Error: Source directory {SRC_DIR} does not exist!")
        return

    DST_DIR.mkdir(parents=True, exist_ok=True)

    md_files = list(SRC_DIR.glob("*.md"))
    txt_files = list(SRC_DIR.glob("*.txt"))
    all_files = md_files + txt_files

    print(f"Found {len(all_files)} files to clean.")

    cleaned_count = 0
    for file_path in all_files:
        try:
            content = file_path.read_text(encoding="utf-8")
            cleaned_content = clean_markdown_content(content)
            
            # Check if cleaned content is not empty
            if cleaned_content:
                dest_path = DST_DIR / file_path.name
                dest_path.write_text(cleaned_content, encoding="utf-8")
                cleaned_count += 1
            else:
                print(f"Warning: File {file_path.name} became empty after cleaning, skipping.")
        except Exception as e:
            print(f"Error cleaning {file_path.name}: {e}")

    print(f"Successfully cleaned and saved {cleaned_count} files to {DST_DIR}")

if __name__ == "__main__":
    main()
