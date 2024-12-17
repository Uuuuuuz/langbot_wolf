from enum import Enum

class Role(Enum):
    """游戏角色"""
    WEREWOLF = "狼人"
    VILLAGER = "平民"
    SEER = "预言家"
    WITCH = "女巫"
    HUNTER = "猎人"

class GameState(Enum):
    """游戏状态"""
    WAITING = "等待中"
    NIGHT = "夜晚"
    DAY = "白天"
    VOTING = "投票中"
    ENDED = "已结束" 