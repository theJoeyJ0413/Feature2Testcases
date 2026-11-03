from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import set_key
import os

from ...config import BACKEND_ROOT
from ...agents.unified_agent.config import Config


router = APIRouter()
ENV_FILE = BACKEND_ROOT/".env"

class AgentSettingsIn(BaseModel):
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"

@router.get("/settings")
def get_settings():
    key = Config.OPENAI_API_KEY or ""
    masked = key[:6] + "******" + key[-4:] if len(key) > 10 else "****"
    return {
        "api_key_masked": masked,
        "base_url": Config.OPENAI_BASE_URL,
        "model": Config.OPENAI_MODEL
    }


@router.put("/settings")
def update_settings(body: AgentSettingsIn):
    if not body.model.strip():
        raise HTTPException(400, "模型不能为空")
    if not body.base_url.strip():
        raise HTTPException(400, "Base URL 不能为空")
    
    # 写.env文件
    set_key(str(ENV_FILE), "OPENAI_MODEL", body.model.strip())
    set_key(str(ENV_FILE), "OPENAI_BASE_URL", body.base_url.strip())
    # 更新内存
    Config.OPENAI_MODEL = body.model.strip()
    Config.OPENAI_BASE_URL = body.base_url.strip()
    # 同步环境变量
    os.environ["OPENAI_MODEL"] = body.model.strip()
    os.environ["OPENAI_BASE_URL"] = body.base_url.strip()

    # API 非空时才更新（空==保持原值）
    if body.api_key.strip():
        set_key(str(ENV_FILE), "OPENAI_API_KEY", body.api_key.strip())
        Config.OPENAI_API_KEY = body.api_key.strip()
        os.environ["OPENAI_API_KEY"] = body.api_key.strip()
    return {"status": "ok"}
