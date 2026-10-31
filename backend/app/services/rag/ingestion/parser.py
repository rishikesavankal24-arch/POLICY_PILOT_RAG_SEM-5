from pathlib import Path
from pypdf import PdfReader


class PolicyDocumentParser:
    """Extract searchable text from an authoritative policy source document."""

    SUPPORTED_SUFFIXES = {".pdf"}

    @classmethod
    def extract_pages(cls, file_path: Path) -> list[dict]:
        path = Path(file_path)
        if path.suffix.lower() not in cls.SUPPORTED_SUFFIXES:
            raise ValueError(f"Unsupported policy document type: {path.suffix}")
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Policy source file not found: {path}")

        reader = PdfReader(str(path))
        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append({"page": page_number, "text": text})

        if not pages:
            raise ValueError(f"No extractable text found in policy PDF: {path.name}")
        return pages

    @classmethod
    def extract_text(cls, file_path: Path) -> str:
        return "\n\n".join(item["text"] for item in cls.extract_pages(file_path))
