"""
LLM 기반 트레이딩 전략
AI 모델에게 시장 상황을 설명하고 매매 결정을 요청
"""
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import json
import os
from ..core.logging_config import logger

# LLM 클라이언트 import (optional)
# Note: These are optional dependencies for LLM-based trading strategies
# They are not required for basic functionality
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


class LLMTradingStrategy:
    """LLM을 이용한 트레이딩 전략"""

    def __init__(
        self,
        model_provider: str = "openai",  # openai, anthropic, google
        model_name: str = "gpt-4",
        temperature: float = 0.3,
        custom_prompt: Optional[str] = None
    ):
        self.model_provider = model_provider
        self.model_name = model_name
        self.temperature = temperature
        self.custom_prompt = custom_prompt

        # API 키 확인
        self.api_key = self._get_api_key()
        if not self.api_key:
            logger.warning(f"{model_provider} API 키가 설정되지 않았습니다.")

    def _get_api_key(self) -> Optional[str]:
        """환경변수에서 API 키 가져오기"""
        key_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY"
        }
        env_var = key_map.get(self.model_provider)
        return os.getenv(env_var) if env_var else None

    def _prepare_market_context(
        self,
        data: pd.DataFrame,
        current_idx: int,
        symbol: str
    ) -> str:
        """현재 시장 상황을 텍스트로 요약"""
        current = data.iloc[current_idx]
        recent = data.iloc[max(0, current_idx - 20):current_idx + 1]

        # 가격 정보
        current_price = current['close']
        price_change_1d = ((current['close'] / recent.iloc[-2]['close']) - 1) * 100 if len(recent) > 1 else 0
        price_change_20d = ((current['close'] / recent.iloc[0]['close']) - 1) * 100 if len(recent) > 1 else 0

        # 기술적 지표
        rsi = current.get('RSI', 'N/A')
        macd = current.get('MACD', 'N/A')
        macd_signal = current.get('MACD_signal', 'N/A')
        sma_20 = current.get('SMA_20', 'N/A')
        sma_50 = current.get('SMA_50', 'N/A')

        context = f"""
## 종목: {symbol}
## 날짜: {current.name.strftime('%Y-%m-%d') if hasattr(current.name, 'strftime') else current.name}

### 가격 정보
- 현재가: ${current_price:.2f}
- 1일 변화: {price_change_1d:+.2f}%
- 20일 변화: {price_change_20d:+.2f}%

### 기술적 지표
- RSI(14): {rsi if isinstance(rsi, str) else f"{rsi:.2f}"}
- MACD: {macd if isinstance(macd, str) else f"{macd:.4f}"}
- MACD Signal: {macd_signal if isinstance(macd_signal, str) else f"{macd_signal:.4f}"}
- SMA(20): {sma_20 if isinstance(sma_20, str) else f"${sma_20:.2f}"}
- SMA(50): {sma_50 if isinstance(sma_50, str) else f"${sma_50:.2f}"}

### 최근 20일 가격 움직임
- 최저가: ${recent['low'].min():.2f}
- 최고가: ${recent['high'].max():.2f}
- 평균 거래량: {recent['volume'].mean():.0f}
"""
        return context

    def _get_default_prompt(self) -> str:
        """기본 프롬프트 템플릿"""
        return """당신은 전문 트레이더입니다. 현재 시장 상황을 분석하고 매매 결정을 내려주세요.

{market_context}

위 정보를 바탕으로 다음 중 하나를 결정해주세요:
1. BUY (매수) - 상승 가능성이 높다고 판단될 때
2. SELL (매도) - 하락 가능성이 높다고 판단될 때
3. HOLD (보유/관망) - 명확한 신호가 없을 때

응답 형식:
{{
  "decision": "BUY" | "SELL" | "HOLD",
  "confidence": 0.0 ~ 1.0,
  "reasoning": "결정 이유를 2-3문장으로 설명"
}}

JSON 형식으로만 응답해주세요."""

    def _call_llm(self, prompt: str) -> Dict:
        """LLM API 호출"""
        if not self.api_key:
            return {
                "decision": "HOLD",
                "confidence": 0.0,
                "reasoning": "API 키가 설정되지 않았습니다."
            }

        try:
            if self.model_provider == "openai" and OPENAI_AVAILABLE:
                return self._call_openai(prompt)
            elif self.model_provider == "anthropic" and ANTHROPIC_AVAILABLE:
                return self._call_anthropic(prompt)
            elif self.model_provider == "google" and GOOGLE_AVAILABLE:
                return self._call_google(prompt)
            else:
                return {
                    "decision": "HOLD",
                    "confidence": 0.0,
                    "reasoning": f"{self.model_provider} 라이브러리가 설치되지 않았습니다."
                }
        except Exception as e:
            logger.error(f"LLM API 호출 오류: {e}")
            return {
                "decision": "HOLD",
                "confidence": 0.0,
                "reasoning": f"오류 발생: {str(e)}"
            }

    def _call_openai(self, prompt: str) -> Dict:
        """OpenAI API 호출"""
        client = openai.OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)

    def _call_anthropic(self, prompt: str) -> Dict:
        """Anthropic Claude API 호출"""
        client = anthropic.Anthropic(api_key=self.api_key)
        message = client.messages.create(
            model=self.model_name,
            max_tokens=1024,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        content = message.content[0].text
        # JSON 파싱 시도
        try:
            return json.loads(content)
        except:
            # JSON이 아닌 경우 기본 응답
            return {
                "decision": "HOLD",
                "confidence": 0.5,
                "reasoning": content[:200]
            }

    def _call_google(self, prompt: str) -> Dict:
        """Google Gemini API 호출"""
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model_name)
        response = model.generate_content(prompt)
        content = response.text
        try:
            return json.loads(content)
        except:
            return {
                "decision": "HOLD",
                "confidence": 0.5,
                "reasoning": content[:200]
            }

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "STOCK"
    ) -> Tuple[pd.Series, pd.Series]:
        """
        LLM을 이용한 매매 신호 생성

        Args:
            data: 가격 및 지표 데이터
            symbol: 종목 코드

        Returns:
            (entry_signals, exit_signals): 매수/매도 신호
        """
        logger.info(f"LLM 전략 실행: {self.model_provider} - {self.model_name}")

        entry_signals = pd.Series(False, index=data.index)
        exit_signals = pd.Series(False, index=data.index)

        # 매 20일마다 LLM에게 물어보기 (API 비용 절감)
        decision_interval = 20
        last_decision = "HOLD"
        decisions_log = []

        for i in range(50, len(data), decision_interval):  # 최소 50일 이후부터
            # 시장 상황 요약
            market_context = self._prepare_market_context(data, i, symbol)

            # 프롬프트 생성
            prompt_template = self.custom_prompt or self._get_default_prompt()
            prompt = prompt_template.format(market_context=market_context)

            # LLM 호출
            response = self._call_llm(prompt)
            decision = response.get("decision", "HOLD")
            confidence = response.get("confidence", 0.0)
            reasoning = response.get("reasoning", "")

            decisions_log.append({
                "date": data.index[i],
                "decision": decision,
                "confidence": confidence,
                "reasoning": reasoning
            })

            # 신호 생성
            if decision == "BUY" and last_decision != "BUY" and confidence > 0.6:
                entry_signals.iloc[i] = True
                last_decision = "BUY"
                logger.info(f"[{data.index[i]}] LLM 매수 신호 (신뢰도: {confidence:.2f}): {reasoning}")

            elif decision == "SELL" and last_decision == "BUY":
                exit_signals.iloc[i] = True
                last_decision = "HOLD"
                logger.info(f"[{data.index[i]}] LLM 매도 신호 (신뢰도: {confidence:.2f}): {reasoning}")

        # 결정 로그 저장 (디버깅용)
        self.decisions_log = decisions_log

        logger.info(f"LLM 전략 완료: 매수 {entry_signals.sum()}회, 매도 {exit_signals.sum()}회")
        return entry_signals, exit_signals


def get_available_llm_models() -> Dict[str, List[str]]:
    """사용 가능한 LLM 모델 목록"""
    return {
        "openai": [
            "gpt-4-turbo-preview",
            "gpt-4",
            "gpt-3.5-turbo"
        ],
        "anthropic": [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ],
        "google": [
            "gemini-pro",
            "gemini-pro-vision"
        ]
    }
