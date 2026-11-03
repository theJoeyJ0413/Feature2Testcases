"""
生成最后的测试用例文档（Excel），并保存到指定目录下
"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
import json
from datetime import datetime
from pathlib import Path

from ..config import Config


class FileGenerator:

    @staticmethod
    def _generate_execl(testcases_text, file_path):
        # 解析 JSON（容忍可能包裹的 ```json 代码块标记），提取出测试用例部分和总结部分
        text = (testcases_text or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"测试用例结果解析失败：{e}；原始内容前200字符：{text[:200]}"
            )
        testcases = data['testcases']
        summarys = data['summary']

        # ============ excel =============
        # 实例化
        wb = Workbook()

        # 激活 work sheet 1 —— 测试用例表
        ws1 = wb.active
        ws1.title = "测试用例"
        header = ["编号", "模块", "优先级", "维度", "场景", "阶段", "标题", "前置操作", "操作步骤", "预期输出", "关联需求"]
        ws1.append(header)

        for testcase in testcases:
            ws1.append([testcase["id"], testcase["module"], testcase["priority"], testcase["dimension"], testcase["scenario"], "、".join(testcase.get("stages", [])), testcase["title"], testcase["precondition"], "\n".join(testcase["steps"]), testcase["expected"], testcase["requirement_ref"]])

        # 激活 work sheet 2 —— 交叉统计表(维度\优先级)
        ws2 = wb.create_sheet("交叉统计表")
        FileGenerator._write_cross_table(ws2, testcases, 1)

        # save
        wb.save(file_path)

    @staticmethod
    def _write_cross_table(ws, testcases, start_now):
        # 构建矩阵表头
        dimensions = ["功能", "性能", "安全", "易用性", "可靠性", "兼容性"]
        priorities = ["P0", "P1", "P2", "P3"]

        matrix = {}
        # { "dimension": {"P0": 1, "P1":3, "P2": 2, "P3": 1"}, ... }
        for tc in testcases:
            dimension = tc["dimension"]
            priority = tc["priority"]
            matrix.setdefault(dimension, {}).setdefault(priority, 0)
            matrix[dimension][priority] += 1

        # 写表头
        headers = ["维度 \\ 优先级"] + priorities + ["小计"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=start_now, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="4472C4", fill_type="solid")
            cell.font = Font(bold=True, color="FFFFFF")
        # 写数据行
        for i, dimension in enumerate(dimensions):
            row = start_now + 1 + i
            ws.cell(row=row, column=1, value=dimension)
            row_sum = 0
            for j, priority in enumerate(priorities):
                val = matrix.get(dimension, {}).get(priority, 0)
                ws.cell(row=row, column=2+j, value=val)
                row_sum += val
            ws.cell(row=row, column=len(priorities)+2, value=row_sum)

    @staticmethod
    def generate(testcases_text, output_format, filename=None, output_dir=None):
        """生成 Excel 并保存，返回文件路径；output_dir 不传时使用 Config 默认输出目录"""
        output_format = output_format or "xlsx"
        output_dir = Path(output_dir) if output_dir else Path(Config.OUTPUT_PATH)

        output_dir.mkdir(parents=True, exist_ok=True)

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"testcases_{timestamp}.{output_format}"
        elif not filename.endswith(f".{output_format}"):
            filename = f"{filename}.{output_format}"

        file_path = output_dir / filename

        FileGenerator._generate_execl(testcases_text, file_path)
        # write
        return str(file_path)
