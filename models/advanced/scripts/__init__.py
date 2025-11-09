from pathlib import Path

# Корень проекта
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Экспортируем основные компоненты
from .multi_agent_env import (
    SingleIntersectionAgent,
    MultiAgentTrafficEnv,
    train_multi_agent,
    test_multi_agent
)

__all__ = [
    'PROJECT_ROOT',
    'SingleIntersectionAgent',
    'MultiAgentTrafficEnv',
    'train_multi_agent',
    'test_multi_agent'
]