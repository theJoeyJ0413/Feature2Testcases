from pathlib import Path
from pypdf import PdfReader


class FileParser:

    @staticmethod
    def is_supported(file_path: str) -> bool:
        """检查文件类型是否支持"""
        path = Path(file_path)
        return path.suffix.lower() in {'.txt', '.md', '.pdf'}

    @staticmethod
    def parse(file_path: str) -> str:
        """解析文件内容"""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()
        if suffix == ".txt":
            return FileParser._parse_txt(file_path)
        elif suffix == ".md":
            return FileParser._parse_txt(file_path)
        elif suffix == ".pdf":
            return FileParser._parse_pdf(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {suffix}")

    @staticmethod
    def _parse_txt(file_path: str) -> str:
        """解析文本文件：txt/md"""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _parse_pdf(file_path: str) -> str:
        """解析PDF文件"""
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n\n".join(text_parts)
