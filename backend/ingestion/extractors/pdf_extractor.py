import io
import logging
import tempfile
import httpx
from pypdf import PdfReader

logger = logging.getLogger(__name__)

def extract_pdf_text_from_bytes(pdf_bytes: bytes) -> str:
    """
    Extracts text from a byte array representing a PDF.
    """
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        text_list = []
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_list.append(page_text)
        return "\n".join(text_list)
    except Exception as e:
        logger.error(f"Failed to extract text from PDF bytes: {e}")
        return ""

async def extract_pdf_text_from_url(url: str, headers: dict = None) -> str:
    """
    Downloads a remote PDF file and extracts its text contents.
    """
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    if headers:
        default_headers.update(headers)

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url, headers=default_headers)
            response.raise_for_status()
            pdf_bytes = response.content
            return extract_pdf_text_from_bytes(pdf_bytes)
    except Exception as e:
        logger.error(f"Failed to fetch or parse PDF from URL {url}: {e}")
        return ""
