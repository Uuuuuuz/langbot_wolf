from typing import Dict, Optional, List
from .enums import Role, GameState
from .player import Player

class Game:
    def __init__(self):
        self.players: Dict[str, Player] = {}  # QQ号 -> 玩家对象
        self.state: GameState = GameState.WAITING
        self.day_count: int = 0  # 天数
        self.group_id: str = ""  # 游戏所在群号
        
        # 场景相关
        self.current_scene: dict = None  # 当前场景
        self.player_locations: Dict[str, str] = {}  # 玩家所在区域 {qq_id: area_name}
        self.area_activities: Dict[str, List[dict]] = {}  # 区域内的活动记录 {area_name: [{player: Player, action: str}]}
        self.night_actions: Dict[str, dict] = {}  # 记录每个玩家的夜间行动
        self.encounters: List[dict] = []  # 记录夜间遭遇
        self.kill_info: Optional[dict] = None  # 记录杀人信息
        
        # 夜晚行动状态
        self.werewolf_killed: Optional[str] = None  # 被狼人杀死的玩家QQ号
        self.seer_checked: bool = False  # 预言家是否已查验
        self.witch_used_potion: bool = False  # 女巫是否已使用解药
        self.witch_used_poison: bool = False  # 女巫是否已使用毒药
        
        # 白天状态
        self.voting_in_progress: bool = False  # 是否在投票阶段
        self.votes: Dict[str, List[str]] = {}  # 投票记录 {被投票者QQ号: [投票者QQ号]}
        self.speech_history: List[dict] = []  # 发言记录
        self.speaking_order: Optional[List[Player]] = None  # 发言顺序
        self.current_speaker_index: int = -1  # 当前发言者索引
        self.pending_death: Optional[str] = None  # 等待猎人开枪的玩家QQ号
        self.questions: List[dict] = []  # 提问记录 [{asker: Player, target: Player, question: str}]
        self.night_thoughts: Dict[str, str] = {}  # AI玩家的夜间思考记录 {qq_id: thought_text}

    def record_kill_info(self, killer: Player, target: Player, location: str, kill_time: str):
        """记录杀人信息"""
        self.kill_info = {
            'killer': killer.qq_id,
            'target': target.qq_id,
            'location': location,
            'time': kill_time
        }
        
        # 记录凶手的行动
        self.record_activity(killer, location, f"在{kill_time}杀死了{target.name}", 
            full_description=f"我在{location}的{kill_time}杀死了{target.name}。为了不被发现，我需要编造一个合理的理由解释我当时在做什么。")

    def is_kill_location(self, area: str) -> bool:
        """检查是否是杀人地点"""
        return self.kill_info and self.kill_info['location'] == area

    def record_encounter(self, observer: Player, target: Player, area: str, action_info: dict):
        """记录玩家遭遇"""
        if not hasattr(self, 'encounters'):
            self.encounters = []
            
        self.encounters.append({
            'observer': observer.qq_id,
            'target': target.qq_id,
            'area': area,
            'time': action_info.get('time', '深夜'),
            'action': action_info['action'],
            'full_description': action_info.get('full_description', '')
        })

    def get_player_encounters(self, player: Player) -> List[dict]:
        """获取玩家的遭遇记录"""
        if not hasattr(self, 'encounters'):
            self.encounters = []
            
        return [e for e in self.encounters if e['observer'] == player.qq_id]

    def reset_night_actions(self):
        """重置夜晚行动状态"""
        self.werewolf_killed = None
        self.seer_checked = False
        self.witch_used_potion = False
        self.witch_used_poison = False
        self.player_locations.clear()
        self.area_activities.clear()
        self.night_actions.clear()
        self.encounters.clear()
        self.kill_info = None

    def record_activity(self, player: Player, area: str, action: str, full_description: str = None):
        """记录玩家的行动"""
        self.night_actions[player.qq_id] = {
            'area': area,
            'action': action,
            'full_description': full_description,
            'day': self.day_count,
            'time': '深夜'  # 默认时间
        }
        self.player_locations[player.qq_id] = area

    def get_area_activities(self, area: str) -> List[dict]:
        """获取区域内的活动记录"""
        return self.area_activities.get(area, [])

    def get_player_location(self, player: Player) -> Optional[str]:
        """获取玩家所在的区域"""
        return self.player_locations.get(player.qq_id)

    def get_players_in_area(self, area: str) -> List[Player]:
        """获取在指定区域的所有玩家"""
        return [p for p in self.players.values() if self.player_locations.get(p.qq_id) == area]

    def add_question(self, asker: Player, target: Player, question: str):
        """添加提问记录"""
        self.questions.append({
            "asker": asker,
            "target": target,
            "question": question
        })

    def get_player_questions(self, player: Player) -> List[dict]:
        """获取针对某个玩家的提问"""
        return [q for q in self.questions if q["target"] == player]

    def get_player_night_action(self, player: Player) -> Optional[dict]:
        """获取玩家的夜间行动记录"""
        return self.night_actions.get(player.qq_id)

    def check_game_over(self) -> Optional[str]:
        """检查游戏是否结束"""
        alive_players = [p for p in self.players.values() if not p.is_dead]
        werewolves = [p for p in alive_players if p.role == Role.WEREWOLF]
        villagers = [p for p in alive_players if p.role != Role.WEREWOLF]

        if not werewolves:
            return "villager"  # 好人胜利
        if len(werewolves) >= len(villagers):
            return "werewolf"  # 狼人胜利
        return None  # 游戏继续