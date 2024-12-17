from typing import Optional
from .enums import Role

class Player:
    def __init__(self, qq_id: str, role: Role, name: str, is_ai: bool = False, personality: dict = None):
        self.qq_id = qq_id  # QQ号
        self.role = role  # 角色
        self.name = name  # 玩家名称
        self.is_dead = False  # 是否死亡
        self.death_reason = None  # 死亡原因
        self.is_ai = is_ai  # 是否是AI玩家
        self.is_protected = False  # 被女巫救过
        self.is_poisoned = False  # 被女巫毒过
        self.role_revealed = False  # 身份是否已经暴露
        self.personality = personality or {}  # AI玩家的性格设定
        
        # 游戏状态
        self.has_voted = False  # 是否已投票

    def die(self, reason: str):
        """玩家死亡"""
        self.is_dead = True
        self.death_reason = reason
        self.role_revealed = True  # 死亡时暴露身份

    def reset_status(self):
        """重置玩家状态（每个新的回合）"""
        self.has_voted = False
        self.is_protected = False
        self.vote_count = 0
        self.last_action_time = None