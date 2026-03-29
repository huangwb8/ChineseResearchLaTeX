"""
LLM Client - 统一的 LLM 客户端接口
支持 Claude、OpenAI 和本地模型
"""

from typing import Optional, Dict, Any
import os


class LLMClient:
    """统一的 LLM 客户端接口"""

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: LLM 配置
                - provider: "claude" | "openai" | "local"
                - model: 模型名称
                - api_key_env: API 密钥环境变量名
                - temperature: 默认温度
                - max_tokens: 最大令牌数
        """
        self.provider = config.get("provider", "claude")
        self.model = config.get("model", "claude-sonnet-4-20250514")
        self.api_key_env = config.get("api_key_env", "ANTHROPIC_API_KEY")
        # temperature 既支持单一数值，也支持按任务类型配置的 dict（analysis/generation/refinement）
        temp_cfg = config.get("temperature", 0.7)
        self.temperature_map: Optional[Dict[str, float]] = None
        if isinstance(temp_cfg, dict):
            self.temperature_map = {k: float(v) for k, v in temp_cfg.items()}
            # 默认使用 generation（更符合“生成器”直觉）；缺失则回退 0.7
            self.temperature = float(self.temperature_map.get("generation", 0.7))
        else:
            self.temperature = float(temp_cfg)
        self.max_tokens = config.get("max_tokens", 4000)

        # 获取 API 密钥
        self.api_key = os.getenv(self.api_key_env)
        if not self.api_key:
            raise ValueError(f"未找到环境变量：{self.api_key_env}")

        # 根据提供商初始化客户端
        self._init_client()

    def _init_client(self):
        """根据提供商初始化客户端"""
        if self.provider == "claude":
            self._init_claude()
        elif self.provider == "openai":
            self._init_openai()
        elif self.provider == "local":
            self._init_local()
        else:
            raise ValueError(f"不支持的 LLM 提供商：{self.provider}")

    def _init_claude(self):
        """初始化 Claude 客户端"""
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("请安装 anthropic 库：pip install anthropic")

    def _init_openai(self):
        """初始化 OpenAI 客户端"""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("请安装 openai 库：pip install openai")

    def _init_local(self):
        """初始化本地模型客户端"""
        # 本地模型的实现可以基于 llama.cpp、ollama 等
        self.client = None
        print("警告：本地模型模式尚未完全实现")

    def complete(
        self,
        prompt: str,
        temperature: float = None,
        max_tokens: int = None,
        response_format: str = None,
        **kwargs
    ) -> str:
        """
        统一的完成接口

        Args:
            prompt: 提示词
            temperature: 温度参数（覆盖默认值）
            max_tokens: 最大令牌数（覆盖默认值）
            response_format: 响应格式（"json" 或 None）
            **kwargs: 其他参数

        Returns:
            str: LLM 响应内容
        """
        temp = temperature if temperature is not None else self.temperature
        temp = float(temp)
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        if self.provider == "claude":
            return self._complete_claude(prompt, temp, tokens, response_format, **kwargs)
        elif self.provider == "openai":
            return self._complete_openai(prompt, temp, tokens, response_format, **kwargs)
        elif self.provider == "local":
            return self._complete_local(prompt, temp, tokens, **kwargs)
        else:
            raise ValueError(f"不支持的提供商：{self.provider}")

    def _complete_claude(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: str = None,
        **kwargs
    ) -> str:
        """使用 Claude 完成请求"""
        # Claude 不直接支持 response_format，需要在 prompt 中指定
        if response_format == "json":
            prompt = f"{prompt}\n\n请只返回 JSON 格式的结果，不要包含其他解释。"

        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt}
            ],
            **kwargs
        )

        return message.content[0].text

    def _complete_openai(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: str = None,
        **kwargs
    ) -> str:
        """使用 OpenAI 完成请求"""
        params = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format == "json":
            params["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**params, **kwargs)
        return response.choices[0].message.content

    def _complete_local(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> str:
        """使用本地模型完成请求"""
        # 本地模型的实现
        raise NotImplementedError("本地模型模式尚未完全实现")

    def set_temperature(self, task_type: str = "default"):
        """
        设置温度参数

        Args:
            task_type: 任务类型
                - "analysis": 分析任务（低温度，0.3）
                - "generation": 生成任务（高温度，0.8）
                - "refinement": 优化任务（中温度，0.5）
                - "default": 使用默认温度
        """
        if self.temperature_map:
            self.temperature = float(self.temperature_map.get(task_type, self.temperature))
            return

        temp_map = {"analysis": 0.3, "generation": 0.8, "refinement": 0.5}
        self.temperature = float(temp_map.get(task_type, self.temperature))
