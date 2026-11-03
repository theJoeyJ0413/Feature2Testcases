"""
统一 Agent - 主控制类

两个阶段共享同一次需求分析结果，保证文档与用例一致：
  阶段1 需求分析：输入 → 需求文档（.md）+ 结构化需求点（.json）
  阶段2 测试用例：结构化需求点 → 测试用例（.xlsx）
"""

import json
from datetime import datetime
from pathlib import Path

from .config import Config
from .src.analyzer import RequirementAnalyzer
from .src.doc_generator import DocumentGenerator
from .src.file_generator import FileGenerator
from .src.file_parser import FileParser
from .src.testcases_generator import TestcasesGenerator


class UnifiedAgent:
    def __init__(self, output_dir: str | Path | None = None):
        """output_dir：产物输出目录，不传时使用 Config 的默认输出目录"""
        self.output_dir = Path(output_dir) if output_dir else Path(Config.OUTPUT_PATH)
        self.file_parser = FileParser()
        self.analyzer = RequirementAnalyzer()
        self.doc_generator = DocumentGenerator()
        self.testcases_generator = TestcasesGenerator()
        self.file_generator = FileGenerator()

    @staticmethod
    def _parse_json(text: str) -> dict:
        """解析 LLM 返回的 JSON 文本（容忍 ```json 代码块包裹），失败抛 ValueError"""
        text = (text or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM 返回内容不是合法 JSON：{e}")

    # ---------- 阶段1：需求分析 ----------
    def analyze(self, input_source: str) -> dict:
        """
        分析输入，生成需求文档和结构化需求点

        Returns:
            dict: {"analysis": 完整分析结果, "doc_path": 文档路径, "features_path": 需求点 JSON 路径}
        """
        user_text = self._get_input_text(input_source)

        print(f"\n📖 输入内容长度: {len(user_text)} 字符")
        print("🔍 正在分析需求...")
        analysis = self.analyzer.analyze(user_text)

        # 保存结构化需求点（供阶段2使用）
        features = RequirementAnalyzer.extract_features(analysis)
        features_path = self._write_json(features, "features")

        print("📝 正在生成需求文档...")
        doc_path = self.doc_generator.generate(analysis, output_dir=self.output_dir)

        print(f"✅ 需求文档: {doc_path}")
        return {
            "analysis": analysis,
            "doc_path": doc_path,
            "features_path": str(features_path),
        }

    # ---------- 阶段2：测试用例生成 ----------
    def generate_testcases(self, features_path: str) -> str:
        """读取结构化需求点，生成测试用例 Excel"""
        print(f"\n📖 读取需求点: {features_path}")
        with open(features_path, "r", encoding="utf-8") as f:
            features = json.load(f)
        features_text = json.dumps(features, ensure_ascii=False, indent=2)

        print("📝 正在生成测试用例...")
        testcases_text = self.testcases_generator.testcases_generator(features_text)

        # 解析并结构化用例 -> 用于后续保存项目时入库
        testcases_data = self._parse_json(testcases_text)
        self._write_json(testcases_data, "testcases")

        print("💾 正在生成测试用例文件...")
        filepath = self.file_generator.generate(testcases_text, "xlsx", output_dir=self.output_dir)

        print(f"✅ 测试用例文件: {filepath}")
        return filepath

    # ---------- 完整流程 ----------
    def process(self, input_source: str) -> dict:
        """完整流程：需求分析 → 测试用例生成"""
        result = self.analyze(input_source)
        result["testcase_path"] = self.generate_testcases(result["features_path"])
        return result

    def _get_input_text(self, input_source: str) -> str:
        """获取输入文本：文件路径（txt/md/pdf）或自然语言"""
        path = Path(input_source)

        if path.exists() and path.is_file():
            if not FileParser.is_supported(input_source):
                raise ValueError(
                    f"不支持的文件类型: {path.suffix}，"
                    f"支持: {', '.join(['.txt', '.md', '.pdf'])}"
                )
            print(f"📂 读取文件: {input_source}")
            return self.file_parser.parse(input_source)

        print("💬 使用自然语言输入")
        return input_source

    def _write_json(self, data: dict, prefix: str) -> Path:
        """把数据写入输出目录下的 JSON 文件，返回路径"""
        output_dir = self.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = output_dir / f"{prefix}_{timestamp}.json"
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path
