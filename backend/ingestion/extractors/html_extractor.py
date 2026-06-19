import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup

def extract_html_data(html_content: str, base_url: str = "") -> Dict[str, Any]:
    """
    Parses HTML text to retrieve clean text content, page title, and all valid links.
    """
    if not html_content:
        return {"title": "", "raw_text": "", "links": [], "pdf_links": []}

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script, style, nav, footer, header elements to avoid noise
    for element in soup(["script", "style", "noscript", "meta", "header", "footer", "nav"]):
        element.decompose()

    # Extract title
    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    # Extract clean text
    text_content = soup.get_text(separator=" ")
    
    # Clean whitespace
    text_content = re.sub(r'\s+', ' ', text_content).strip()

    # Extract links
    links = []
    pdf_links = []
    
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
            
        # Resolve relative URLs if base_url is provided
        if base_url and not href.startswith(("http://", "https://")):
            # Simple URL resolving
            if href.startswith("/"):
                # strip ending slash of base_url if present
                base = re.sub(r'/$', '', base_url)
                # Find domain root
                domain_match = re.match(r'(https?://[^/]+)', base)
                if domain_match:
                    resolved_url = f"{domain_match.group(1)}{href}"
                else:
                    resolved_url = f"{base}{href}"
            else:
                base = base_url if base_url.endswith("/") else f"{base_url}/"
                resolved_url = f"{base}{href}"
        else:
            resolved_url = href

        # Classify as normal link or PDF link
        if resolved_url.lower().endswith(".pdf"):
            if resolved_url not in pdf_links:
                pdf_links.append(resolved_url)
        else:
            if resolved_url not in links:
                links.append(resolved_url)

    return {
        "title": title,
        "raw_text": text_content,
        "links": links,
        "pdf_links": pdf_links
    }
