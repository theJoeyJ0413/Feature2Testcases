"""
根据需求点列表生成测试用例 —— 使用 LLM

输入：阶段1 需求分析产出的结构化需求点（features JSON）
输出：测试用例 JSON，交给 FileGenerator 生成 Excel

一条需求 ——> 多条用例
场景类型	说明	示例
正向	正常操作，验证功能可用	输入有效书名，搜索成功
边界	临界值、极限情况	搜索关键词只有1个字符
异常	错误输入、异常流程	搜索不存在的书名
非功能	性能/安全/兼容等	1000人同时搜索，响应 < 1秒
"""

from openai import OpenAI

from ..config import Config


class TestcasesGenerator:
    def __init__(self):
        Config.validate()
        self.client = OpenAI(
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_BASE_URL,
            timeout=Config.REQUEST_TIMEOUT,
        )
        self.model = Config.OPENAI_MODEL

    def _build_user_prompt(self, features_text):
        return f"""请根据以下需求点列表（来自需求分析阶段），设计完整的测试用例集合：

        {features_text}

        要求：
        1. 每个需求点至少覆盖正向、边界、异常各一条用例
        2. 有非功能性要求的需求，需额外生成对应维度的用例
        3. 严格按 JSON 格式输出
        """

    def _get_system_prompt(self) -> str:
        return """你是一个资深的软件测试工程师，擅长根据需求文档设计全面的测试用例。

        ## 你的任务
        根据输入的需求点列表，为每个需求点设计完整的测试用例集合。

        ## 测试用例字段说明

        | 字段 | 说明 | 示例 |
        |------|------|------|
        | id | 唯一编号，格式 TC-三位序号 | TC-001 |
        | module | 所属模块 | 图书管理 |
        | priority | 优先级 P0(核心)/P1(重要)/P2(一般)/P3(低) | P0 |
        | dimension | 测试维度 | 功能/性能/易用性/可靠性/兼容性/安全 |
        | scenario | 场景类型 | 正向/边界/异常 |
        | stages | 测试阶段（可多选，数组） | 冒烟/通道/灰度/系统/回归/验收，如 ["系统", "回归"] |
        | title | 用例标题，一句话说清测试什么 | 使用书名关键词搜索图书 |
        | precondition | 前置条件（执行前需要满足的状态） | 用户已登录，系统中已有100本图书 |
        | steps | 操作步骤，编号列出，每步一个具体动作 | 1. 进入搜索页面 2. 输入关键词... |
        | expected | 预期结果，明确、可判断、可验证 | 搜索结果在1秒内展示，列表按相关度排序 |
        | requirement_ref | 关联的需求编号 | FEATURE-003 |

        ## 输出格式
        请严格按照以下 JSON 格式输出：

        {
        "testcases": [
            {
            "id": "TC-001",
            "module": "模块名",
            "priority": "P0",
            "dimension": "功能",
            "scenario": "正向",
            "stages": ["系统"],
            "title": "用例标题",
            "precondition": "前置条件，如无则填'无'",
            "steps": [
                "1. 具体操作步骤一",
                "2. 具体操作步骤二",
                "3. 具体操作步骤三"
            ],
            "expected": "明确的预期结果",
            "requirement_ref": "FEATURE-001"
            }
        ],
        "summary": {
            "total": 10,
            "by_dimension": {"功能性": 5, "性能": 2, "安全性": 1, "兼容性": 1, "易用性": 1},
            "by_priority": {"P0": 3, "P1": 4, "P2": 2, "P3": 1},
            "by_scenario": {"正向场景": 5, "边界检验": 3, "异常场景": 2}
        }
        }

        ## 用例设计规则

        ### 1. 覆盖规则
        每个需求点必须生成以下用例：
        - ✅ 至少 1 条正向功能用例（验证功能正常可用）
        - ✅ 至少 1 条边界用例（临界值、特殊输入）
        - ✅ 至少 1 条异常用例（错误操作、异常流程）
        - ✅ 如果需求有非功能性要求，每个维度至少 1 条

        ### 2. 优先级规则
        | 优先级 | 适用场景 |
        |--------|----------|
        | P0 | 核心功能的主流程，阻塞性问题 |
        | P1 | 重要功能的正常流程，关键边界场景 |
        | P2 | 辅助功能、一般边界和异常场景 |
        | P3 | 低频场景、极端边界、UI细节 |

        ### 3. 步骤编写规则
        - 每步只做一个操作
        - 步骤描述具体，包含输入数据
        ✅ "在搜索框中输入'Python编程'"
        ❌ "输入搜索关键词"
        - 步骤之间逻辑连贯，可被非技术人员执行
        - 一般 3~7 步为宜

        ### 4. 预期结果规则
        - 必须可观察、可判断
        ✅ "页面展示搜索结果列表，共10条记录"
        ❌ "搜索功能正常"
        - 如果有性能要求，写明量化指标
        ✅ "搜索结果在1秒内展示"
        ❌ "搜索结果快速展示"

        ### 5. 编号规则
        - 编号格式：TC-三位序号，如 TC-001
        - 序号在所属需求（requirement_ref 指向的需求）内递增：001, 002, 003...
        - 不同需求的用例编号互不影响，可以从 TC-001 重新开始

        ## 注意事项
        - 用例描述通俗易懂，确保非技术人员也能理解和执行
        - 前置条件要实际可行，不要写无法准备的条件
        - 只输出 JSON，不要输出其他内容
        """

    def testcases_generator(self, features_text):
        prompt = self._build_user_prompt(features_text)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
        )
        testcases_text = response.choices[0].message.content
        if not testcases_text:
            raise ValueError("LLM 返回内容为空，请重试（可能是网络波动或接口限流）")
        return testcases_text
