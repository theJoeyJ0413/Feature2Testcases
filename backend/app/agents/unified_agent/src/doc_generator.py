"""
文档生成器 - 将分析结果中的文档章节渲染为 Markdown 并保存

注意：分析结果里的 features（需求点）部分由测试用例阶段使用，这里只渲染文档章节。
"""

from datetime import datetime
from pathlib import Path

from ..config import Config


class DocumentGenerator:

    @staticmethod
    def generate(result: dict, output_format: str = "md", filename: str = None, output_dir: str = None) -> str:
        """生成文档并保存，返回文件路径；output_dir 不传时使用 Config 默认输出目录"""
        content = DocumentGenerator._render(result, output_format)

        output_dir = Path(output_dir) if output_dir else Path(Config.OUTPUT_PATH)
        output_dir.mkdir(parents=True, exist_ok=True)

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"requirements_{timestamp}.{output_format}"
        elif not filename.endswith(f".{output_format}"):
            filename = f"{filename}.{output_format}"

        file_path = output_dir / filename
        file_path.write_text(content, encoding="utf-8")
        return str(file_path)

    @staticmethod
    def _render(result: dict, output_format: str) -> str:
        # 解析失败时 LLM 原样返回的内容直接写入
        if "raw" in result:
            return result["raw"]
        if output_format == "txt":
            return DocumentGenerator._to_text(result)
        return DocumentGenerator._to_markdown(result)

    @staticmethod
    def _section_md(title: str, items) -> str:
        """渲染一个 Markdown 章节"""
        if isinstance(items, str):
            items = [items]
        items = items or []
        if not items:
            return ""
        lines = [f"## {title}", ""]
        lines += [f"- {item}" for item in items]
        return "\n".join(lines)

    @staticmethod
    def _to_markdown(result: dict) -> str:
        blocks = []
        title = result.get("project_name") or "需求分析文档"
        blocks.append(f"# {title}\n")

        overview = (result.get("project_overview") or "").strip()
        if overview:
            blocks.append(f"{overview}\n")

        blocks.append(DocumentGenerator._section_md("核心需求", result.get("core_requirements")))
        blocks.append(DocumentGenerator._section_md("非功能需求", result.get("non_functional_requirements")))
        blocks.append(DocumentGenerator._section_md("用户场景", result.get("user_scenarios")))
        blocks.append(DocumentGenerator._section_md("技术建议", result.get("tech_suggestions")))
        blocks.append(DocumentGenerator._section_md("风险与注意事项", result.get("risks")))

        return "\n".join(b for b in blocks if b).strip() + "\n"

    @staticmethod
    def _section_text(title: str, items) -> str:
        """渲染一个纯文本章节"""
        if isinstance(items, str):
            items = [items]
        items = items or []
        if not items:
            return ""
        lines = [f"【{title}】", ""]
        lines += [f"- {item}" for item in items]
        return "\n".join(lines)

    @staticmethod
    def _to_text(result: dict) -> str:
        blocks = []
        title = result.get("project_name") or "需求分析文档"
        blocks.append(f"{title}\n")

        overview = (result.get("project_overview") or "").strip()
        if overview:
            blocks.append(f"{overview}\n")

        blocks.append(DocumentGenerator._section_text("核心需求", result.get("core_requirements")))
        blocks.append(DocumentGenerator._section_text("非功能需求", result.get("non_functional_requirements")))
        blocks.append(DocumentGenerator._section_text("用户场景", result.get("user_scenarios")))
        blocks.append(DocumentGenerator._section_text("技术建议", result.get("tech_suggestions")))
        blocks.append(DocumentGenerator._section_text("风险与注意事项", result.get("risks")))

        return "\n".join(b for b in blocks if b).strip() + "\n"
