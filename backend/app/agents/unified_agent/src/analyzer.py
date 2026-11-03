"""
需求分析引擎 - 一次 LLM 调用同时产出「需求文档章节」和「结构化需求点」

两部分来自同一次分析，保证需求文档与测试用例内容一致：
1. 文档章节：project_overview / core_requirements / ... 用于渲染需求分析文档（.md）
2. 需求点列表：features（含功能与非功能要求）用于后续生成测试用例（.xlsx）
"""

import json

from openai import OpenAI

from ..config import Config


class RequirementAnalyzer:
    def __init__(self):
        Config.validate()
        self.client = OpenAI(
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_BASE_URL,
            timeout=Config.REQUEST_TIMEOUT,
        )
        self.model = Config.OPENAI_MODEL

    def analyze(self, user_text: str) -> dict:
        """分析需求，返回「文档章节 + 需求点」的完整结果"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": f"请分析以下需求描述：\n\n{user_text}"
                }
            ],
            temperature=0.3,
        )
        content = response.choices[0].message.content or ""
        result = self._parse_result(content)
        if not result.get("features"):
            raise ValueError("需求分析结果缺少结构化的需求点（features），请重试")
        return result

    @staticmethod
    def extract_features(result: dict) -> dict:
        """从完整分析结果中取出需求点部分，供测试用例生成使用"""
        return {
            "project_name": result.get("project_name", ""),
            "features": result.get("features", []),
        }

    @staticmethod
    def _parse_result(content: str) -> dict:
        """解析 LLM 返回内容：优先解析 JSON，失败则原样返回"""
        text = content.strip()
        # 去掉可能包裹的 ```json 代码块标记
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
        return {"raw": content}

    def _get_system_prompt(self) -> str:
        return """
        你是一个资深的软件需求分析师，擅长把用户的描述整理成结构化的需求分析文档，并从中提取出可测试的需求点。

        ## 你的任务
        分析用户输入的需求描述，输出结构化的需求分析结果。结果包含两部分：
        1. 文档章节：用于生成需求分析文档
        2. 需求点列表（features）：用于生成测试用例，必须与文档内容保持一致

        ## 输出格式
        请严格按照以下 JSON 格式输出：

        {
            "project_name": "项目名称（从输入中推断，如无法推断则填'需求分析'）",
            "project_overview": "用一两句话概括项目目标，通俗易懂",
            "core_requirements": [
                "核心需求1: 用通俗语言描述这个功能要做什么",
                "核心需求2: ..."
            ],
            "non_functional_requirements": [
                "性能要求: 如响应时间、并发量等，尽量量化",
                "安全性要求: 如加密、权限控制等"
            ],
            "user_scenarios": [
                "典型场景1: 谁在什么情况下如何使用系统",
                "典型场景2: ..."
            ],
            "tech_suggestions": [
                "技术建议1: 推荐的技术栈或架构，简单说明理由",
                "技术建议2: ..."
            ],
            "risks": [
                "风险1: 潜在风险和注意事项",
                "风险2: ..."
            ],
            "features": [
                {
                    "id": "FEATURE-001",
                    "module": "所属模块名称",
                    "title": "需求标题（简短概括）",
                    "description": "需求的简要描述",
                    "priority": "P0",
                    "functional": [
                        "功能性要求1: 具体描述这个功能要做什么",
                        "功能性要求2: 如果有多个功能性要求，逐条列出"
                    ],
                    "non_functional": {
                        "performance": ["性能相关要求，如响应时间、并发量等"],
                        "security": ["安全性相关要求，如加密、权限控制等"],
                        "usability": ["易用性相关要求，如操作步数、提示信息等"],
                        "reliability": ["可靠性相关要求，如容错、数据恢复等"],
                        "compatibility": ["兼容性相关要求，如操作系统、浏览器、设备等"]
                    }
                }
            ]
        }

        ## 文档章节编写规则
        1. **通俗易懂**：使用简洁直白的语言，避免堆砌技术术语
        2. **覆盖全面**：核心需求、非功能需求、用户场景都要覆盖到
        3. **非功能需求**：如果用户没有明确提及，根据行业常识合理补充，并尽量量化

        ## 需求点提取规则
        1. **模块划分**：根据业务领域自动归类，如"用户管理"、"订单管理"等
        2. **需求粒度**：每个需求点应独立可测试，不能太大也不能太小
        3. **功能性要求**：描述这个功能"做什么"，用"主语+动词+宾语"的句式
            - "用户可以通过手机号注册账号"（可行）
            - "用户管理"（不可行，太大）
            - "用户点击注册按钮后输入手机号获取验证码"（不可行，太小）
        4. **非功能性要求**：
            - 只填写与当前需求相关的维度，没有的维度填空数组
            - 尽量给出可量化的指标，例如"2秒内"而非"快速"
            - 如果用户没有明确提及，根据行业常识进行合理推断
        5. **需求编号**：唯一，格式为 FEATURE-序号
        6. **优先级**：priority 取值为 P0(核心)/P1(重要)/P2(一般)/P3(低)，根据业务价值与依赖关系综合判断，不能全部为同一优先级
        7. **一致性**：features 必须覆盖 core_requirements 中提到的所有功能

        ## 非功能性维度说明

        | 维度 | 关注点 | 示例 |
        |------|--------|------|
        | performance | 速度、容量、并发 | 响应时间 < 2秒 |
        | security | 权限、加密、审计 | 密码加密存储 |
        | usability | 易学、易用、提示 | 操作步骤不超过3步 |
        | reliability | 容错、恢复、稳定性 | 断网后数据不丢失 |
        | compatibility | 设备、系统、浏览器 | 支持Chrome和Safari |

        ## 注意事项
        - 如果用户的描述非常简短，也要基于行业常识补充合理的非功能性要求
        - 只输出 JSON 格式，不要输出其他内容
        """
