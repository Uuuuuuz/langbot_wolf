import os
import json
import random
import asyncio
from typing import Optional, Dict, List, AsyncGenerator
from pkg.plugin.models import *
from pkg.plugin.host import PluginHost
from pkg.plugin.context import BasePlugin, handler, register
from pkg.plugin import events
from pkg.plugin.context import EventContext
from pkg.platform.types import message as platform_message
from pkg.platform.types.message import Plain
from .game import Game
from .player import Player
from .enums import Role, GameState
from pkg.command.operator import CommandOperator, operator_class
from pkg.command import entities
import typing
from .scene_generator import get_random_scene, format_game_start_message
import aiohttp
import datetime

@operator_class(name="lrs", help="狼人杀游戏命令", privilege=1)
class WerewolfOperator(CommandOperator):
    def __init__(self, host):
        super().__init__(host)
        self.config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        self.log_path = os.path.join(os.path.dirname(__file__), 'game.log')
        self.config = self.load_config()
        self.game: Optional[Game] = None
        self.api_keys = [

        ]
        self.ai_keys = {}  # 存储AI玩家和他们的key的映射
        self.api_url = "https://api.openai-hk.com/v1/chat/completions"
        self.plugin = None

        # AI玩家性格和背景设定
        self.ai_personalities = [
            # 基础性格模板
            {
                "name": "李静",
                "gender": "女",
                "age": 22,
                "personality": "温柔善良，说话轻声细语，善于观察他人的细微表情",
                "background": "大学生，心理学专业，擅长分析人的行为动机",
                "behavior_style": "经常用手指轻轻卷着头发，说话时会微微歪头"
            },
            {
                "name": "王刚",
                "gender": "男",
                "age": 35,
                "personality": "沉稳冷静，逻辑性强，说话简洁有力",
                "background": "刑警队长，经验丰富，习惯性分析案情",
                "behavior_style": "常常双手抱胸，目光如炬地观察他人"
            },
            {
                "name": "张萌",
                "gender": "女",
                "age": 18,
                "personality": "活泼开朗，说话语速较快，情绪丰富",
                "background": "高中生，推理小说爱好者，思维跳跃",
                "behavior_style": "说话时手势多，经常摇晃着双腿"
            },
            {
                "name": "赵华",
                "gender": "男",
                "age": 45,
                "personality": "稳重老练，说话慢条斯理，不轻易下结论",
                "background": "律师，善于讲道理，注重证据",
                "behavior_style": "时常推一推眼镜，说话时喜欢用手指点桌面"
            },
            {
                "name": "陈雨",
                "gender": "女",
                "age": 28,
                "personality": "机智灵活，反应快，说话幽默",
                "background": "记者，习惯抓住关键信息，善于引导话题",
                "behavior_style": "经常歪着头思考，说话时会不自觉地整理头发"
            },
            # 新增性格模板
            {
                "name": "郑思",
                "gender": "女",
                "age": 24,
                "personality": "细心谨慎，观察入微，逻辑性强",
                "background": "研究生，心理学方向，擅长行为分析",
                "behavior_style": "说话时会不自觉地整理衣角，目光专注"
            },
            {
                "name": "黄磊",
                "gender": "男",
                "age": 40,
                "personality": "幽默风趣，思维活跃，善于活跃气氛",
                "background": "脱口秀演员，擅长即兴发挥，观察力敏锐",
                "behavior_style": "说话时手势丰富，常常带着笑意"
            },
            {
                "name": "马兰",
                "gender": "女",
                "age": 35,
                "personality": "沉着冷静，分析力强，善于推理",
                "background": "数学教师，习惯用逻辑思维解决问题",
                "behavior_style": "说话有条理，常常用手指比划重点"
            },
            {
                "name": "徐风",
                "gender": "男",
                "age": 29,
                "personality": "热情开朗，反应敏捷，富有正义感",
                "background": "消防员，习惯快速判断局势，行动果断",
                "behavior_style": "站姿挺拔，说话掷地有声，目光坚定"
            },
            {
                "name": "白雪",
                "gender": "女",
                "age": 27,
                "personality": "温婉可人，心思细腻，善解人意",
                "background": "幼儿教师，擅长观察情绪变化，耐心细致",
                "behavior_style": "说话轻柔，常带着温暖的笑容，举止优雅"
            }
        ]

    def log_game(self, message: str):
        """记录游戏日志"""
        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            print(f"写入日志失败：{str(e)}")

    async def send_group_message(self, group_id: str, text: str):
        """发送群消息"""
        if self.plugin:
            await self.plugin.send_group_message(group_id, text)

    async def send_private_message(self, user_id: str, text: str):
        """发送私聊消息"""
        if self.plugin:
            await self.plugin.send_private_message(user_id, text)

    def load_config(self) -> dict:
        """加载配置文件"""
        default_config = {
            "min_players": 6,
            "max_players": 12,
            "roles": {
                "6": {"werewolf": 2, "villager": 2, "seer": 1, "witch": 1},
                "7": {"werewolf": 2, "villager": 3, "seer": 1, "witch": 1},
                "8": {"werewolf": 3, "villager": 3, "seer": 1, "witch": 1},
                "9": {"werewolf": 3, "villager": 4, "seer": 1, "witch": 1},
                "10": {"werewolf": 3, "villager": 4, "seer": 1, "witch": 1, "hunter": 1},
                "11": {"werewolf": 4, "villager": 4, "seer": 1, "witch": 1, "hunter": 1},
                "12": {"werewolf": 4, "villager": 5, "seer": 1, "witch": 1, "hunter": 1}
            }
        }

        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            else:
                # 创建默认配置文件
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                return default_config
        except Exception as e:
            print(f"加载配置文件失败：{str(e)}")
            return default_config

    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件失败：{str(e)}")

    async def assign_roles(self, player_count: int) -> Dict[str, Role]:
        """分配角色"""
        roles_config = self.config["roles"].get(str(player_count))
        if not roles_config:
            raise ValueError(f"不支持{player_count}人游戏")

        # 创建角色列表
        roles = []
        for role_name, count in roles_config.items():
            role = Role[role_name.upper()]
            roles.extend([role] * count)

        # 随机打乱角色
        random.shuffle(roles)

        # 分配给玩家
        result = {}
        player_ids = list(self.game.players.keys())
        for i, role in enumerate(roles):
            result[player_ids[i]] = role

        return result

    async def execute(self, context: entities.ExecuteContext) -> typing.AsyncGenerator[entities.CommandReturn, None]:
        command = context.crt_params[0] if context.crt_params else "help"
        response = None

        try:
            if command == "start":
                if self.game and self.game.state != GameState.ENDED:
                    response = "游戏已经在进行中"
                else:
                    self.game = Game()
                    self.game.state = GameState.WAITING
                    self.game.group_id = str(context.query.launcher_id)
                    scene = await get_random_scene()
                    self.game.current_scene = scene
                    response = format_game_start_message(scene)

            elif command == "join":
                if not self.game or self.game.state == GameState.ENDED:
                    response = "游戏还未创建，请先使用!lrs start创建游戏"
                elif self.game.state != GameState.WAITING:
                    response = "游戏已经开始，无法加入"
                elif len(self.game.players) >= self.config["max_players"]:
                    response = "游戏人数已满"
                else:
                    qq_id = str(context.query.sender_id)
                    if qq_id in self.game.players:
                        response = "已经在游戏中了"
                    else:
                        self.game.players[qq_id] = Player(
                            qq_id=qq_id,
                            role=Role.VILLAGER,  # 临时角色，后面会重新分配
                            name=f"玩家{len(self.game.players)+1}"
                        )
                        response = f"加入成功！当前玩家数：{len(self.game.players)}/{self.config['min_players']}"

            elif command == "begin":
                if not self.game or self.game.state == GameState.ENDED:
                    response = "游戏还未创建，请先使用!lrs start创建游戏"
                elif self.game.state != GameState.WAITING:
                    response = "游戏已经开始"
                elif len(self.game.players) < self.config["min_players"]:
                    # 添加AI玩家补充到最小人数
                    ai_count = self.config["min_players"] - len(self.game.players)
                    await self.add_ai_players(ai_count)
                    
                # 分配角色
                roles = await self.assign_roles(len(self.game.players))
                for qq_id, role in roles.items():
                    self.game.players[qq_id].role = role
                
                # 私聊告知角色
                role_info = "【游戏开始】\n\n【玩家列表】\n"
                for qq_id, player in self.game.players.items():
                    if not player.is_ai:
                        role_msg = f"你的角色是：{player.role.value}"
                        if player.role == Role.WEREWOLF:
                            # 显示队友
                            werewolves = [p for p in self.game.players.values() if p.role == Role.WEREWOLF and p.qq_id != qq_id]
                            if werewolves:
                                role_msg += "\n你的狼人队友是：" + "、".join(w.name for w in werewolves)
                        await self.send_private_message(qq_id, role_msg)
                    role_info += f"• {player.name}{'[AI]' if player.is_ai else ''}\n"
                
                self.game.state = GameState.NIGHT
                self.game.day_count = 1

                # 场景描述
                scene_info = f"\n【场景】{self.game.current_scene['name']}\n"
                scene_info += f"【背景】{self.game.current_scene['story']}\n"
                scene_info += f"【天气】{self.game.current_scene['weather']}\n"
                scene_info += f"【当前场景】\n{self.game.current_scene['current_scene']}\n"
                scene_info += "\n【可前往的区域】\n"
                for area_name, area_desc in self.game.current_scene['areas'].items():
                    scene_info += f"• {area_name}：{area_desc}\n"
                
                # 添加胜利条件说明
                scene_info += "\n【胜利条件】\n"
                scene_info += "• 狼人阵营：杀死足够多的好人\n"
                scene_info += "• 好人阵营：找出所有狼人，或者活到第4天白天\n"
                
                response = f"{role_info}\n当前共{len(self.game.players)}名玩家\n{scene_info}\n进入第1天夜晚...\n\n"
                
                # 夜晚阶段提示
                werewolves = [p for p in self.game.players.values() if p.role == Role.WEREWOLF and not p.is_ai]
                if werewolves:
                    response += "狼人请私聊使用 !lrs kill <目标> <地点> <时间> 杀人\n"
                seers = [p for p in self.game.players.values() if p.role == Role.SEER and not p.is_ai]
                if seers:
                    response += "预言家请私聊使用 !lrs see <目标> - 查验身份\n"
                witches = [p for p in self.game.players.values() if p.role == Role.WITCH and not p.is_ai]
                if witches:
                    response += "女巫请私聊使用 !lrs save - 使用解药，或 !lrs poison <目标> - 使用毒药\n"

            elif command == "kill":
                if not self.game or self.game.state != GameState.NIGHT:
                    response = "当前不是狼人行动时间"
                else:
                    qq_id = str(context.query.sender_id)
                    player = self.game.players.get(qq_id)
                    if not player or player.role != Role.WEREWOLF:
                        response = "你不是狼人"
                    elif self.game.werewolf_killed is not None:
                        response = "今晚已经决�����了行动"
                    elif len(context.crt_params) < 2:
                        response = "��使用格式：!lrs kill <目标> <地点> <时间>\n例如：!lrs kill 张三 教室 凌晨2点\n或输入 !lrs kill none 表示不杀人"
                    else:
                        target_name = context.crt_params[1]
                        if target_name.lower() == "none":
                            self.game.werewolf_killed = ""
                            response = "你选择了今晚不杀人"
                        else:
                            if len(context.crt_params) < 4:
                                response = "请指定杀人地点和时间"
                            else:
                                target = self.find_player_by_name_or_id(target_name)
                                location = context.crt_params[2]
                                kill_time = context.crt_params[3]
                                
                                if not target:
                                    response = "目标不存在"
                                elif target.is_dead:
                                    response = "目标已经死亡"
                                elif target.role == Role.WEREWOLF:
                                    response = "不能杀死同伴"
                                elif location not in self.game.current_scene['areas']:
                                    response = f"无效的地点。可选地点：{', '.join(self.game.current_scene['areas'].keys())}"
                                else:
                                    self.game.werewolf_killed = target.qq_id
                                    # 记录杀人信息
                                    self.game.record_kill_info(player, target, location, kill_time)
                                    response = f"已选择在{location}的{kill_time}杀死{target.name}"
                        await self.process_ai_actions()

            elif command == "see":
                if not self.game or self.game.state != GameState.NIGHT:
                    response = "当前不是预言家行动时间"
                else:
                    qq_id = str(context.query.sender_id)
                    player = self.game.players.get(qq_id)
                    if not player or player.role != Role.SEER:
                        response = "你不是预言家"
                    elif self.game.seer_checked:
                        response = "今晚已经查验过人了"
                    elif len(context.crt_params) < 2:
                        response = "请指定要查验的人（QQ号或玩家名字）"
                    else:
                        target_name = " ".join(context.crt_params[1:])
                        target = self.find_player_by_name_or_id(target_name)
                        if not target:
                            response = "目标不存在"
                        elif target.is_dead:
                            response = "目标已经死亡"
                        else:
                            self.game.seer_checked = True
                            response = f"查验结果：{target.name} 是{'狼人' if target.role == Role.WEREWOLF else '好'}"
                            await self.process_ai_actions()

            elif command == "save":
                if not self.game or self.game.state != GameState.NIGHT:
                    response = "当前不是女巫行动时间"
                else:
                    qq_id = str(context.query.sender_id)
                    player = self.game.players.get(qq_id)
                    if not player or player.role != Role.WITCH:
                        response = "你不是女巫"
                    elif self.game.witch_used_potion:
                        response = "你已经使用过解药了"
                    elif not self.game.werewolf_killed:
                        response = "今晚没有人被狼人杀死"
                    else:
                        self.game.witch_used_potion = True
                        target = self.game.players[self.game.werewolf_killed]
                        target.is_protected = True
                        self.game.werewolf_killed = None
                        response = f"你使用解药救活了 {target.name}"
                        await self.process_ai_actions()

            elif command == "poison":
                if not self.game or self.game.state != GameState.NIGHT:
                    response = "当前不是女巫行动时间"
                else:
                    qq_id = str(context.query.sender_id)
                    player = self.game.players.get(qq_id)
                    if not player or player.role != Role.WITCH:
                        response = "你不是女巫"
                    elif self.game.witch_used_poison:
                        response = "你已经使用过毒药了"
                    elif len(context.crt_params) < 2:
                        response = "请指定要毒的人（QQ号或玩家名字）"
                    else:
                        target_name = " ".join(context.crt_params[1:])
                        target = self.find_player_by_name_or_id(target_name)
                        if not target:
                            response = "目标不存在"
                        elif target.is_dead:
                            response = "目标已经死亡"
                        else:
                            self.game.witch_used_poison = True
                            target.is_poisoned = True
                            response = f"你使用毒药毒死了 {target.name}"
                            await self.process_ai_actions()

            elif command == "innight":
                if not self.game:
                    response = "游戏还未开始"
                elif self.game.state == GameState.NIGHT:
                    response = "已经是夜晚阶段了"
                else:
                    # 进入夜晚阶段
                    response = await self.enter_night_phase()
                    
                    # 如果是AI玩家，自动处理他们的行动
                    await self.process_ai_actions()

            elif command == "help":
                response = """狼人杀游戏指令说明：
游戏开始前：
1. !lrs start - 创建新游戏
2. !lrs join - 加入游戏
3. !lrs begin - 开始游戏（不足人数时用AI补充）

游戏进行中：
4. !lrs status - 查看游戏状态和存活玩家
5. !lrs fy <发言内容> - 在自己的回合发言
6. !lrs next - 结束当前发言，进入下一个玩家
7. !lrs sf - 查看自己的身份
8. !lrs innight - 手动进入夜晚阶段

夜晚阶段：
9. !lrs kill <玩家名字> <地点> <时间> - 狼人杀人
10. !lrs see <玩家名字> - 预言家查验
11. !lrs save - 女巫救人
12. !lrs poison <玩家名字> - 女巫毒人
13. !lrs endnight - 结束夜晚阶段

白天阶段：
14. !lrs vote <玩家名字> - 投票处决玩家
15. !lrs shoot <玩家名字> - 猎人开枪（死亡时使用）"""

            elif command == "endnight":
                if not self.game or self.game.state != GameState.NIGHT:
                    response = "现在不是夜晚阶段"
                else:
                    # 处理所有AI玩家的行动
                    await self.process_ai_actions()
                    
                    # 处理夜晚结果
                    death_report = "天亮...\n"
                    deaths = []

                    # 处理狼人杀人
                    if self.game.werewolf_killed and self.game.werewolf_killed != "" and not self.game.players[self.game.werewolf_killed].is_protected:
                        victim = self.game.players[self.game.werewolf_killed]
                        victim.die("被狼人杀死")
                        deaths.append(victim.name)

                    # 处理女巫毒人
                    poisoned = [p for p in self.game.players.values() if p.is_poisoned]
                    for victim in poisoned:
                        victim.die("被女巫毒死")
                        deaths.append(victim.name)

                    if deaths:
                        death_report += f"昨晚，{', '.join(deaths)}被杀死了。"
                    else:
                        death_report += "昨晚是平安夜，没有人死亡。"

                    # 检查游戏是否结束
                    game_result = self.game.check_game_over()
                    if game_result:
                        self.game.state = GameState.ENDED
                        death_report += f"\n游戏结束，{'好人' if game_result == 'villager' else '狼人'}获胜！"
                    else:
                        self.game.state = GameState.DAY
                        death_report += "\n\n请使用 !lrs next 开始发言。"

                    # 重置夜晚状态
                    self.game.reset_night_actions()

                    response = death_report

            elif command == "fy":
                if not self.game or self.game.state != GameState.DAY:
                    response = "现在不是发言阶段"
                else:
                    # 查是否到发言者
                    current_speaker = self.game.speaking_order[self.game.current_speaker_index] if hasattr(self.game, 'speaking_order') and self.game.current_speaker_index >= 0 else None
                    qq_id = str(context.query.sender_id)
                    
                    if not current_speaker:
                        response = "还未开始发言阶段，请等待"
                    elif current_speaker.qq_id != qq_id:
                        response = f"现在是 {current_speaker.name} 的发言时间"
                    elif len(context.crt_params) < 2:
                        response = "请输入发言内容"
                    else:
                        # 记录玩家发言
                        speech = " ".join(context.crt_params[1:])
                        self.game.speech_history.append({
                            "name": self.game.players[qq_id].name,
                            "role": self.game.players[qq_id].role,
                            "speech": speech
                        })
                        response = f"{self.game.players[qq_id].name}：{speech}"

            elif command == "next":
                if not self.game or self.game.state != GameState.DAY:
                    response = "现在不是发言阶段"
                else:
                    # 初始化发言顺序
                    if not hasattr(self.game, 'speaking_order'):
                        alive_players = [p for p in self.game.players.values() if not p.is_dead]
                        self.game.speaking_order = random.sample(alive_players, len(alive_players))
                        self.game.current_speaker_index = -1
                        self.game.speech_history = []
                        response = f"发言顺序：" + " -> ".join(p.name for p in self.game.speaking_order)
                        self.game.current_speaker_index = 0
                        first_player = self.game.speaking_order[0]
                        response += f"\n\n请 {first_player.name} 开始发言"
                        
                        # 如果第一个是AI，自动发言
                        if first_player.is_ai:
                            ai_speech = await self.generate_ai_speech(first_player, [])
                            self.game.speech_history.append({
                                "name": first_player.name,
                                "role": first_player.role,
                                "speech": ai_speech
                            })
                            response += f"\n{first_player.name}：{ai_speech}"
                        yield entities.CommandReturn(text=response)
                        return
                    
                    # 进入下一个发言者
                    self.game.current_speaker_index += 1
                    if self.game.current_speaker_index >= len(self.game.speaking_order):
                        # 所有人都发言完毕
                        self.game.voting_in_progress = True
                        response = "所有玩家发言完毕，开始投票！\n请使用 !lrs vote <玩家名字> 进行投票"
                    else:
                        current_player = self.game.speaking_order[self.game.current_speaker_index]
                        response = f"请 {current_player.name} 开始发言"
                        
                        if current_player.is_ai:
                            # AI根据历史发言生成回复
                            ai_speech = await self.generate_ai_speech(current_player, self.game.speech_history or [])
                            self.game.speech_history.append({
                                "name": current_player.name,
                                "role": current_player.role,
                                "speech": ai_speech
                            })
                            response += f"\n{current_player.name}：{ai_speech}"

            elif command == "sf":
                if not self.game or self.game.state == GameState.ENDED:
                    response = "游戏还未开始"
                else:
                    qq_id = str(context.query.sender_id)
                    player = self.game.players.get(qq_id)
                    if not player:
                        response = "你不是游戏玩家"
                    else:
                        response = f"你的角色是：{player.role.value}"
                        if player.role == Role.WEREWOLF:
                            # 显示狼人队友
                            werewolves = [p for p in self.game.players.values() if p.role == Role.WEREWOLF and p.qq_id != qq_id]
                            if werewolves:
                                response += "\n你的狼人队友是：" + "、".join(w.name for w in werewolves)
                        # 显示存活状态
                        response += f"\n当前状态：{'已死' if player.is_dead else '存活'}"
                        if player.is_dead and player.death_reason:
                            response += f"（{player.death_reason}）"

            elif command == "status":
                if not self.game:
                    response = "游戏还未创建"
                else:
                    alive_players = [p for p in self.game.players.values() if not p.is_dead]
                    dead_players = [p for p in self.game.players.values() if p.is_dead]
                    
                    response = f"游戏状态：{self.game.state.value}\n"
                    response += f"【当前天数】第{self.game.day_count}天（好人需要活到第4天白天）\n"
                    response += f"【场景】{self.game.current_scene['name']}\n"
                    response += f"【天气】{self.game.current_scene['weather']}\n"
                    response += f"【当前场景】\n{self.game.current_scene['current_scene']}\n"
                    response += f"\n【存活玩家】（{len(alive_players)}人）：\n"
                    
                    # 每个存活的 AI 玩家生成一个简短的状态描述
                    ai_status_tasks = []
                    for player in alive_players:
                        role_info = f"（{player.role.value}）" if player.role_revealed else ""
                        response += f"• {player.name}{role_info}{'[AI]' if player.is_ai else ''}\n"
                        if player.is_ai:
                            ai_status_tasks.append(self.generate_ai_status(player, f"请描述一下 {player.name} 的状态："))
                    
                    # 等待所有 AI 状态生成完成
                    if ai_status_tasks:
                        ai_responses = await asyncio.gather(*ai_status_tasks)
                        response += "\n【AI 玩家状态】\n"
                        for i, player in enumerate([p for p in alive_players if p.is_ai]):
                            response += f"• {player.name}：{ai_responses[i]}\n"
                    
                    if dead_players:
                        response += f"\n【死亡玩家（{len(dead_players)}人）：\n"
                        for player in dead_players:
                            response += f"• {player.name}（{player.role.value}）{'[AI]' if player.is_ai else ''}\n"

            elif command == "vote":
                if not self.game or self.game.state != GameState.DAY:
                    response = "现在不是投票阶段"
                elif not self.game.voting_in_progress:
                    response = "还未到投票阶段"
                else:
                    qq_id = str(context.query.sender_id)
                    player = self.game.players.get(qq_id)
                    if not player:
                        response = "你不是游戏玩家"
                    elif player.is_dead:
                        response = "死亡玩家不投"
                    elif len(context.crt_params) < 2:
                        response = "请指定要投票的玩家（玩家名字），或输入 !lrs vote none 放弃投票"
                    else:
                        target_name = " ".join(context.crt_params[1:])
                        if target_name.lower() == "none":
                            response = f"{player.name} 放弃了投票"
                            self.log_game(f"{player.name} 放弃了投票")
                        else:
                            target = self.find_player_by_name_or_id(target_name)
                            if not target:
                                response = "目标不存在"
                            elif target.is_dead:
                                response = "不能投死玩家"
                            else:
                                # 记录投票
                                if target.qq_id not in self.game.votes:
                                    self.game.votes[target.qq_id] = []
                                self.game.votes[target.qq_id].append(qq_id)
                                response = f"{player.name} 投给了 {target.name}"

                        # 检查是否所有存活玩都已投
                        alive_players = [p for p in self.game.players.values() if not p.is_dead]
                        voted_players = set()
                        for votes in self.game.votes.values():
                            voted_players.update(votes)
                        
                        if len(voted_players) >= len(alive_players):
                            # 所有人都投票完毕，处理投票结果
                            await self.process_vote()
                        else:
                            # 让AI玩家投票
                            for ai_player in [p for p in alive_players if p.is_ai and p.qq_id not in voted_players]:
                                vote_target = await self.get_ai_vote_decision(ai_player)
                                if vote_target:
                                    if vote_target.qq_id not in self.game.votes:
                                        self.game.votes[vote_target.qq_id] = []
                                    self.game.votes[vote_target.qq_id].append(ai_player.qq_id)
                                    response += f"\n{ai_player.name} 投票给了 {vote_target.name}"
                                else:
                                    response += f"\n{ai_player.name} 放弃了投票"
                            
                            # 再次检查是否所有人都投票完毕
                            voted_players = set()
                            for votes in self.game.votes.values():
                                voted_players.update(votes)
                            if len(voted_players) >= len(alive_players):
                                await self.process_vote()

            elif command == "nextround":
                if not self.game:
                    response = "游戏还未开始"
                elif self.game.state == GameState.NIGHT:
                    # 结算夜晚阶段
                    await self.check_night_end()
                    response = None  # 消息已经在check_night_end中发送
                elif self.game.state == GameState.DAY:
                    if not hasattr(self.game, 'speaking_order'):
                        # 初始化发言顺序
                        alive_players = [p for p in self.game.players.values() if not p.is_dead]
                        self.game.speaking_order = random.sample(alive_players, len(alive_players))
                        self.game.current_speaker_index = -1
                        self.game.speech_history = []
                        response = "发言顺序：" + " -> ".join(p.name for p in self.game.speaking_order)
                        self.game.current_speaker_index = 0
                        first_player = self.game.speaking_order[0]
                        response += f"\n\n请 {first_player.name} 开始发言"
                        if first_player.is_ai:
                            ai_speech = await self.generate_ai_speech(first_player, [])
                            self.game.speech_history.append({
                                "name": first_player.name,
                                "role": first_player.role,
                                "speech": ai_speech
                            })
                            response += f"\n{first_player.name}：{ai_speech}"
                    else:
                        response = "请使用 !lrs next 继续发言"

            elif command == "huida":
                if not self.game or self.game.state != GameState.DAY:
                    response = "现在不是提问时间"
                elif len(context.crt_params) < 2:
                    response = "请指定要回答的玩家（玩家名字）"
                else:
                    target_name = " ".join(context.crt_params[1:])
                    target = self.find_player_by_name_or_id(target_name)
                    if not target:
                        response = "目标玩家不存在"
                    elif target.is_dead:
                        response = "死亡玩家无法回答问题"
                    elif not target.is_ai:
                        response = "只能询问AI玩家"
                    else:
                        # 获取该玩家收到的问题
                        questions = self.game.get_player_questions(target)
                        if not questions:
                            response = f"{target.name} 没有收到任何问题"
                        else:
                            # 让AI回答最近的问题
                            answer = await self.get_ai_answer(target, questions[-1])
                            response = f"{target.name} 回答：{answer}"

            elif command == "wen":
                if not self.game or self.game.state != GameState.DAY:
                    response = "现在不是提问时间"
                elif len(context.crt_params) < 3:
                    response = "请使用格式：!lrs wen <玩家名字> <问题内容>"
                else:
                    target_name = context.crt_params[1]
                    question = " ".join(context.crt_params[2:])
                    target = self.find_player_by_name_or_id(target_name)
                    if not target:
                        response = "目标玩家不存在"
                    elif target.is_dead:
                        response = "死亡玩家无法回答问题"
                    elif not target.is_ai:
                        response = "只能询问AI玩家"
                    else:
                        qq_id = str(context.query.sender_id)
                        asker = self.game.players.get(qq_id)
                        if not asker:
                            response = "你不是游戏玩家"
                        else:
                            # 记录问题
                            self.game.add_question(asker, target, question)
                            response = f"{asker.name} 问 {target.name}：{question}\n请使用 !lrs huida {target.name} 获取回答"

        except Exception as e:
            response = f"发生错误：{str(e)}"
            print(f"游戏错误：{str(e)}")

        if response:
            yield entities.CommandReturn(text=response)

    async def clear_hunter_pending(self, delay: int):
        """清除猎人开枪等待状"""
        await asyncio.sleep(delay)
        if self.game and self.game.pending_death:
            self.game.pending_death = None
            # 广播消息
            await self.send_group_message(self.game.group_id, "猎人放弃机会")

    async def add_ai_players(self, count: int):
        """添加AI玩家"""
        # 随机打乱API keys以分配给AI
        available_keys = self.api_keys.copy()
        random.shuffle(available_keys)
        
        # 确保有足够的key
        if len(available_keys) < count:
            raise ValueError(f"没有足够的API key供AI使用（需要{count}个，只有{len(available_keys)}个）")
        
        # 中国古代名字库
        chinese_names = {
            "male": [
                "子轩", "浩然", "天宇", "文韬", "雨泽", "晓峰", "子默", "修远", "志强", "子骞",
                "明辉", "浩轩", "鸿涛", "思源", "博文", "振华", "弘毅", "文昊", "子瑜", "皓轩"
            ],
            "female": [
                "语嫣", "梦琪", "雨桐", "诗雨", "思涵", "若雪", "梦露", "静怡", "雨欣", "美琪",
                "雨晴", "语芙", "晓梦", "紫萱", "欣怡", "凌波", "灵韵", "芸芸", "芷若", "怜雪"
            ]
        }
        
        # 姓氏库
        surnames = ["赵", "钱", "孙", "李", "周", "吴", "郑", "王", "冯", "陈", 
                   "褚", "卫", "蒋", "沈", "韩", "杨", "朱", "秦", "尤", "许"]
        
        # 已使用的名字集合
        used_names = set()
        
        # 清空之前的AI key映射
        self.ai_keys.clear()
        
        for i in range(count):
            # 随机选择一个性格模板
            personality = random.choice(self.ai_personalities)
            
            # 根据性格的性别选择名字
            gender = "male" if personality["gender"] == "男" else "female"
            surname = random.choice(surnames)
            name_pool = chinese_names[gender]
            
            # 生成完整名字
            while True:
                full_name = surname + random.choice(name_pool)
                if full_name not in used_names:
                    used_names.add(full_name)
                    break
            
            ai_id = f"ai_{i+1}"
            
            # 为这个AI分配一个固定的key
            self.ai_keys[ai_id] = available_keys[i]  # 使用未打乱的顺序分配key
            
            # 创建AI玩家
            self.game.players[ai_id] = Player(
                qq_id=ai_id,
                role=Role.VILLAGER,  # 临时角色，后面会重新分配
                name=full_name,
                is_ai=True,
                personality=personality
            )
            
            self.log_game(f"创建AI玩家：{full_name}（{personality['background']}），使用key：{available_keys[i][:8]}...")

    async def process_ai_actions(self):
        """处理AI玩家的行动"""
        if not self.game or not self.game.state:
            return

        ai_players = {id: player for id, player in self.game.players.items() if player.is_ai and not player.is_dead}
        if not ai_players:
            return

        # 按角色优先级排序：狼人 -> 预言家 -> 女巫 -> 普通村民
        role_priority = {
            Role.WEREWOLF: 1,
            Role.SEER: 2,
            Role.WITCH: 3,
            Role.VILLAGER: 4,
            Role.HUNTER: 5
        }
        
        sorted_players = sorted(ai_players.items(), key=lambda x: role_priority.get(x[1].role, 999))

        for ai_id, ai_player in sorted_players:
            if self.game.state == GameState.NIGHT:
                # 狼人行动
                if ai_player.role == Role.WEREWOLF and self.game.werewolf_killed is None:
                    decision = await self.get_ai_decision(ai_player, "werewolf_kill")
                    if decision.get("action") == "kill":
                        target_id = decision.get("target")
                        if target_id:
                            self.game.werewolf_killed = target_id
                            # 记录杀人信息
                            self.game.kill_info = {
                                'location': decision.get('area', '未知地点'),
                                'time': decision.get('time', '深夜')
                            }
                    else:
                        self.game.werewolf_killed = ""  # 不杀人

                # 预言家行动
                elif ai_player.role == Role.SEER and not self.game.seer_checked:
                    decision = await self.get_ai_decision(ai_player, "seer_check")
                    if decision.get("target"):
                        self.game.seer_checked = True
                        target = self.game.players[decision["target"]]
                        is_werewolf = target.role == Role.WEREWOLF
                        self.log_game(f"[预言家查验] {target.name} 是{'狼人' if is_werewolf else '好人'}")

                # 女巫行动
                elif ai_player.role == Role.WITCH:
                    if not self.game.witch_used_potion and self.game.werewolf_killed:
                        decision = await self.get_ai_decision(ai_player, "witch_action")
                        if decision.get("action") == "save":
                            self.game.witch_used_potion = True
                            self.game.werewolf_killed = None
                        elif decision.get("action") == "poison" and decision.get("target"):
                            self.game.witch_used_poison = True
                            target = self.game.players[decision["target"]]
                            target.is_poisoned = True
                            # 记录毒杀信��
                            target.poison_info = {
                                'location': decision.get('area', '未知地点'),
                                'time': decision.get('time', '深夜')
                            }

                # 普通村民行动
                else:
                    decision = await self.get_ai_decision(ai_player, "normal_action")
                    if decision.get("action") == "normal":
                        self.game.record_activity(ai_player, 
                            decision.get('area', '未知地点'),
                            f"在{decision.get('time', '深夜')}时{decision.get('action', '四处走动')}",
                            f"我在{decision.get('area', '某处')}巡查。")

    def get_role_prompt(self, role: Role, is_night: bool = False) -> str:
        """获取角色提示词"""
        if role == Role.WEREWOLF:
            if is_night:
                return """作为狼人，你的目标是在白天隐藏身份，并在夜晚袭击人。

夜间行动指南��
1. 请选择今晚要袭击的目标，保行动低调并保持合
2. 注意队协作，确保攻击的目标与其他狼人的行一致
3. 分析哪些玩家可能是特殊角色如预言家或女巫），优先考虑他们作为目标

请直接回复：选择xxx 或 选择不杀人"""
            else:
                return """作为狼人，你需要在白天隐藏身份并迷惑其他玩家。

发言指南：
1. 隐藏你的狼人身份，模仿好人的思维逻辑
2. 找机会挑一名玩家，制造他们可疑的线索
3. 巧妙回应别人的质疑，用模糊的语句转移视线
4. 与队友配合暗示目标，逐步引投票

策略提示：
- 避免主动暴露自己，不要急于带节奏
- 试着分散怀疑目标，好人阵营无法统一意见
- 适度'反水'，即假装质疑你的队友狼人，增加自身可信度

请直接给出发言内容，不要有任何额外说明。"""

        elif role == Role.SEER:
            if is_night:
                return """作为预言家，你可以在夜晚查验一名玩家的真实身。

查验指南：
1. 选择最可疑或最需要确认身份的玩家
2. 优先查验关键位置的玩家
3. 为白天的发言收集信息

请直接回复：查验xxx"""
            else:
                return """作为预言家，你需要帮助好人找出狼人。

发言指南：
1. 可以试着暗自己的查验结果，但保持低调
2. 若被狼人怀疑，以清晰地报告查验过的身份
3. 注保护自己，免过早暴露身份

请直接给出发言内容，不要有任何额外说明。"""

        elif role == Role.WITCH:
            if is_night:
                return """作为女巫，你拥有一瓶解药和一瓶毒药。

行动指南：
1. 解药可以救活被狼人杀死的玩家
2. 毒药可以毒死一名玩家
3. 每种药只能使用一次，请谨慎选择

请直接回复：使用解药救人 或 使用毒药毒死xxx 或 不使用药水"""
            else:
                return """作为女巫，你需要合理使用药水帮好人阵营。

发言指南：
1. 可以隐晦地暗示自己的行动，但不要直接表明份
2. 观察其他玩家的反应，寻找狼人的破绽
3. 记录每个人的发言，为使用毒药做准备

请直接给出发言内容，不要有任何额外说明。"""

        elif role == Role.HUNTER:
            return """作为猎人，你死亡时可以开枪带走一名玩家。

发言指南：
1. 保持低调，避免早早暴露身份
2. 密切观察其他玩家的发言
3. 记录可疑的玩家，为可能的开枪时机做准备

请直接给出发言内容，不要任何额外说明。"""

        else:  # 普通村民
            return """作为普通人，你需要通过察和推找出狼人。

发言指南：
1. 仔细观察每个人发言，找破绽
2. 记录反常表现比如逻辑混乱或言辞闪烁
3. 与其他好人建立信任，合力找出狼人

请直接给出发言内容，不要有任何额外说明。"""

    async def get_ai_decision(self, ai_player: Player, action_type: str) -> dict:
        """获取AI的决策"""
        game_state = self.get_game_state_info()
        role_prompt = self.get_role_prompt(ai_player.role, is_night=True)
        personality = ai_player.personality
        
        # 获取可用的区域列表
        available_areas = list(self.game.current_scene['areas'].keys())
        
        prompt = f"""你是一个狼人杀游戏中的{ai_player.role.value}。

你的身份信息：
姓名：{personality['name']}
性别：{personality['gender']}
年龄：{personality['age']}岁
性格：{personality['personality']}
背景：{personality['background']}
行为习惯：{personality['behavior_style']}

当前游戏状态：
{game_state}

可以前往的区域：
{', '.join(available_areas)}

{role_prompt}

请详细描述你的思考过程和行动决策。你需要提供以下信息：
1. 分析当前的局势
2. 评估每个玩家的可疑程度
3. 解释你选择行动的原因
4. 你对其他玩家的看法

然后，请在最后一行给出你的具体行动决策，格式如下：

如果你是狼人：
决定：杀死 <目标玩家> 在 <具体地点> 时间是 <具体时间>
或
决定：今晚不杀人

如果你是预言家：
决定：查验 <目标玩家>

如果你是女巫：
决定：使用解药
或
决定：使用毒药毒死 <目标玩家>
或
决定：不使用药水

如你是普通村民：
决定：前往 <具体地点> 在 <具体时间> <具体行动>

注意：
- 地点必须从可用区域列表中选择
- 时间应该是凌晨1-4点之间
- 行动要符合你的性格特点和角色身份"""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self.ai_keys[ai_player.qq_id]}"},
                    json={
                        "model": "claude-3-sonnet-20240229",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 2000
                    }
                ) as response:
                    result = await response.json()
                    if "choices" in result and result["choices"]:
                        decision_text = result["choices"][0]["message"]["content"]
                        self.log_game(f"[AI思考] {ai_player.name}：{decision_text}")
                        
                        # 记录思考过程
                        if not hasattr(self.game, 'night_thoughts'):
                            self.game.night_thoughts = {}
                        self.game.night_thoughts[ai_player.qq_id] = decision_text
                        
                        # 解析决策
                        last_line = decision_text.strip().split('\n')[-1]
                        if last_line.startswith("决定："):
                            decision = last_line[3:].strip()  # 去掉"决定："前缀
                            
                            if ai_player.role == Role.WEREWOLF and action_type == "werewolf_kill":
                                if "不杀人" in decision:
                                    return {"action": "skip"}
                                elif "杀死" in decision:
                                    # 解析格式：杀死 <目标> 在 <地点> 时间是 <时间>
                                    parts = decision.split()
                                    target_name = parts[1]
                                    location = parts[3]
                                    time = parts[5:]
                                    target = self.find_player_by_name_or_id(target_name)
                                    if target and location in available_areas:
                                        self.game.record_activity(ai_player, location,
                                            f"在{' '.join(time)}试图杀死{target.name}",
                                            f"我在{location}散步，突然听到一些动静。")
                                        return {"action": "kill", "target": target.qq_id, "area": location, "time": ' '.join(time)}
                            
                            elif ai_player.role == Role.SEER and action_type == "seer_check":
                                if "查验" in decision:
                                    target_name = decision.split("查验")[1].strip()
                                    target = self.find_player_by_name_or_id(target_name)
                                    if target:
                                        is_werewolf = target.role == Role.WEREWOLF
                                        chosen_area = random.choice(available_areas)
                                        self.game.record_activity(ai_player, chosen_area,
                                            f"查验了{target.name}的身份，发现是{'狼人' if is_werewolf else '好人'}",
                                            f"我在{chosen_area}读书，思考着大家的表现。")
                                        return {"target": target.qq_id, "result": "werewolf" if is_werewolf else "villager"}
                                
                            elif ai_player.role == Role.WITCH and action_type == "witch_action":
                                if "使用解药" in decision and not self.game.witch_used_potion and self.game.werewolf_killed:
                                    chosen_area = random.choice(available_areas)
                                    self.game.record_activity(ai_player, chosen_area,
                                        "使用解药救人",
                                        f"我在{chosen_area}制作药水，研究草药。")
                                    return {"action": "save"}
                                elif "使用毒药" in decision and not self.game.witch_used_poison:
                                    target_name = decision.split("毒死")[1].strip()
                                    target = self.find_player_by_name_or_id(target_name)
                                    if target:
                                        chosen_area = random.choice(available_areas)
                                        self.game.record_activity(ai_player, chosen_area,
                                            f"使用毒药毒死{target.name}",
                                            f"我在{chosen_area}收集药材，研究新配方。")
                                        return {"action": "poison", "target": target.qq_id}
                            
                            else:
                                # 解析普通村民的行动：前往 <地点> 在 <时间> <行动>
                                if "前往" in decision:
                                    parts = decision.split()
                                    location = parts[1]
                                    time_index = parts.index("在") + 1
                                    time = parts[time_index]
                                    action = " ".join(parts[time_index+1:])
                                    if location in available_areas:
                                        self.game.record_activity(ai_player, location,
                                            f"在{time}时{action}",
                                            f"我在{location}{action}。")
                                        return {"action": "normal", "area": location, "time": time}
                            
        except Exception as e:
            print(f"AI决策失败：{str(e)}")
            self.log_game(f"AI决策失败：{str(e)}")
        
        return {}

    async def check_night_end(self):
        """检查夜晚是否结束"""
        if not self.game or self.game.state != GameState.NIGHT:
            return

        # 处理所有AI玩家的行动
        await self.process_ai_actions()
        
        # 处理夜晚结果
        death_report = f"天亮了...\n{self.game.current_scene['_full_data']['day_description']}\n\n"
        deaths = []

        # 处理狼人杀人
        if self.game.werewolf_killed and self.game.werewolf_killed != "" and not self.game.players[self.game.werewolf_killed].is_protected:
            victim = self.game.players[self.game.werewolf_killed]
            # 获取杀人信息
            kill_info = getattr(self.game, 'kill_info', {})
            location = kill_info.get('location', '未知地点')
            kill_time = kill_info.get('time', '深夜')
            victim.die(f"被狼人杀死，尸体在{location}被发现，推测死亡时间在{kill_time}")
            deaths.append(f"{victim.name}（尸体在{location}被发现）")

        # 处理女巫毒人
        poisoned = [p for p in self.game.players.values() if p.is_poisoned]
        for victim in poisoned:
            # 获取毒杀信息
            poison_info = getattr(victim, 'poison_info', {})
            location = poison_info.get('location', '未知地点')
            death_time = poison_info.get('time', '深夜')
            victim.die(f"被毒死，尸体在{location}被发现，推测死亡时间在{death_time}")
            deaths.append(f"{victim.name}（尸体在{location}被发现）")

        if deaths:
            death_report += f"昨晚，{', '.join(deaths)}。"
            # 添加现场描述
            death_report += "\n\n【现场描述】\n"
            for player in self.game.players.values():
                if player.is_dead and player.death_reason and "昨晚" in player.death_reason:
                    death_report += f"• {player.name}：{player.death_reason}\n"
        else:
            death_report += "昨晚是平安夜，没有人死亡。"

        # 检查游戏是否结束
        game_result = self.game.check_game_over()
        if game_result:
            self.game.state = GameState.ENDED
            death_report += f"\n游戏结束，{'好人' if game_result == 'villager' else '狼人'}获胜！"
        else:
            self.game.state = GameState.DAY
            death_report += "\n\n请使用 !lrs next 开始发言。"

        # 重置夜晚状态
        self.game.reset_night_actions()

        await self.send_group_message(self.game.group_id, death_report)

    async def enter_night_phase(self):
        """进入夜晚阶段"""
        if not self.game:
            return "游戏还未开始"
            
        # 重置投票状态
        self.game.voting_in_progress = False
        self.game.votes.clear()
        self.game.speaking_order = None
        self.game.current_speaker_index = -1
        self.game.speech_history = []

        # 进入夜晚阶段
        self.game.state = GameState.NIGHT  # 直接设置状态为夜晚
        self.game.day_count += 1  # 增加天数
        
        # 重置夜晚相关状态
        self.game.werewolf_killed = None
        self.game.seer_checked = False
        self.game.witch_used_potion = False
        self.game.witch_used_poison = False
        
        # 发送夜晚开始的消息
        night_message = f"\n进入第{self.game.day_count}天夜晚...\n{self.game.current_scene['_full_data']['night_description']}\n\n"
        
        # 给活着的玩家发送提示
        alive_players = [p for p in self.game.players.values() if not p.is_dead]
        werewolves = [p for p in alive_players if p.role == Role.WEREWOLF and not p.is_ai]
        seers = [p for p in alive_players if p.role == Role.SEER and not p.is_ai]
        witches = [p for p in alive_players if p.role == Role.WITCH and not p.is_ai]
        
        if werewolves:
            night_message += "狼人请私聊使用 !lrs kill <目标> <地点> <时间> 杀人\n"
        if seers:
            night_message += "预言家请私聊使用 !lrs see <目标> 查验身份\n"
        if witches:
            night_message += "女巫请私聊使用 !lrs save 使用解药，或 !lrs poison <目标> 使用毒药\n"
            
        night_message += "\n所有玩家行动完毕后，请使用 !lrs endnight 结束夜晚"
        
        await self.send_group_message(self.game.group_id, night_message)
        
        # 处理AI玩家的夜间行动
        await self.process_ai_actions()
        
        return night_message

    async def get_ai_area_decision(self, ai_player: Player) -> Optional[dict]:
        """获取AI的区域行动决策"""
        game_state = self.get_game_state_info()
        personality = ai_player.personality
        
        prompt = f"""你是一个狼人杀游戏中的{ai_player.role.value}。

你的身份信息：
姓名：{personality['name']}
性别：{personality['gender']}
年龄：{personality['age']}岁
性格：{personality['personality']}
背景{personality['background']}
行习惯：{personality['behavior_style']}

当前场景：
{self.game.current_scene['description']}

可以前往的区域：
"""
        for area_name, area_desc in self.game.current_scene['areas'].items():
            prompt += f"- {area_name}：{area_desc}\n"

        prompt += """
请根据你的性格和身份，选择一个区域并描述你要在那里做什么。记住：
1. 你的行动要符合你的性格特点
2. 要考虑区域的特点和可能风险
3. 描述你选择该区域的原因
4. 详细描述你在那里的具体行动

请用一人称详细描述你的想法和行动，后在后一行给出决定，格式为：
前往xxx区域：[具体行动描述]"""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self.ai_keys[ai_player.qq_id]}"},
                    json={
                        "model": "claude-3-sonnet-20240229",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 2000
                    }
                ) as response:
                    result = await response.json()
                    if "choices" in result and result["choices"]:
                        decision_text = result["choices"][0]["message"]["content"]
                        self.log_game(f"[AI思考] {ai_player.name}：{decision_text}")
                        
                        # 解析决策
                        last_line = decision_text.strip().split('\n')[-1]
                        if "前往" in last_line and "：" in last_line:
                            area = last_line.split("前往")[1].split("：")[0].strip()
                            action = last_line.split("：")[1].strip()
                            if area in self.game.current_scene['areas']:
                                return {"area": area, "action": action}
        except Exception as e:
            print(f"AI区域决策失败：{str(e)}")
            self.log_game(f"AI区域决策失败：{str(e)}")
        
        return None

    async def get_ai_answer(self, ai_player: Player, question: dict) -> str:
        """获取AI的回答"""
        game_state = self.get_game_state_info()
        personality = ai_player.personality
        
        prompt = f"""你是一个狼人杀游戏中的{ai_player.role.value}。

你的身份信息：
姓名：{personality['name']}
性别：{personality['gender']}
年龄：{personality['age']}岁
性格：{personality['personality']}
背景：{personality['background']}
行为习惯：{personality['behavior_style']}

当前游戏状态：
{game_state}

你收到了一个问题：
{question['asker'].name}问你：{question['question']}

请根据你的性格和身份回答这个问题。注意：
1. 回答要符合你的性格特点
2. 不要暴露自己的真实身份
3. 可以适当隐瞒或误导
4. 要表现出合理的情绪和态度

请用第一人称回答这个问题。"""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self.ai_keys[ai_player.qq_id]}"},
                    json={
                        "model": "claude-3-sonnet-20240229",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 1000
                    }
                ) as response:
                    result = await response.json()
                    if "choices" in result and result["choices"]:
                        answer = result["choices"][0]["message"]["content"].strip()
                        return answer
        except Exception as e:
            print(f"AI回答失败：{str(e)}")
            
        return "（思考中...）"

    async def process_next_speaker(self):
        """处理下一个发言玩家"""
        if not self.game:
            return None
            
        # 初始化发言顺序（如果还没有）
        if not hasattr(self.game, 'speaking_order') or not self.game.speaking_order:
            alive_players = [p for p in self.game.players.values() if not p.is_dead]
            self.game.speaking_order = random.sample(alive_players, len(alive_players))
            self.game.current_speaker_index = -1
            if not hasattr(self.game, 'speech_history'):
                self.game.speech_history = []

        self.game.current_speaker_index += 1
        if self.game.current_speaker_index >= len(self.game.speaking_order):
            # 所有人都发言完毕
            self.game.voting_in_progress = True
            return "所有玩家发言完毕，开始投票！\n请使用 !lrs vote <玩家名字> 进行投票"

        current_player = self.game.speaking_order[self.game.current_speaker_index]
        response = f"请 {current_player.name} 开始发言"
        
        if current_player.is_ai:
            # AI根据历史发言生成回复
            ai_speech = await self.generate_ai_speech(current_player, self.game.speech_history or [])
            if not hasattr(self.game, 'speech_history'):
                self.game.speech_history = []
            self.game.speech_history.append({
                "name": current_player.name,
                "role": current_player.role,
                "speech": ai_speech
            })
            response += f"\n{current_player.name}：{ai_speech}"
            # 自动进入下一个玩家
            next_response = await self.process_next_speaker()
            if next_response:
                response += f"\n\n{next_response}"
        
        return response

    async def send_group_message(self, group_id: str, text: str):
        """发送群消息"""
        if self.plugin:
            await self.plugin.send_group_message(group_id, text)

    async def send_private_message(self, user_id: str, text: str):
        """发送私聊消息"""
        if self.plugin:
            await self.plugin.send_private_message(user_id, text)

    async def generate_ai_speech(self, ai_player: Player, speech_history: List[dict]) -> str:
        """生成AI玩家的发言"""
        game_state = self.get_game_state_info()
        role_prompt = self.get_role_prompt(ai_player.role)
        personality = ai_player.personality
        
        # 获取AI的夜间行动记录和遭遇记录
        night_action = self.game.get_player_night_action(ai_player)
        encounters = self.game.get_player_encounters(ai_player)
        
        # 获取昨晚的思考记录
        ai_thoughts = ""
        if hasattr(self.game, 'night_thoughts') and ai_player.qq_id in self.game.night_thoughts:
            ai_thoughts = self.game.night_thoughts[ai_player.qq_id]
        
        prompt = f"""你是一个狼人杀游戏中的玩家。记住：永远不要在发言中透露自己的真实身份！不要说我是，也不要说作为。

你的身份信息：
姓名：{ai_player.name}
性别：{personality['gender']}
年龄：{personality['age']}岁
性格：{personality['personality']}
背景：{personality['background']}
行为习惯：{personality['behavior_style']}

当前场景：
{self.game.current_scene['current_scene']}

你昨晚的真实行动：
地点：{night_action['area'] if night_action else '未记录'}
时间：{night_action['time'] if night_action else '未记录'}
行动：{night_action['full_description'] if night_action else '未记录'}

你昨晚的思考过程：
{ai_thoughts if ai_thoughts else '（没有记录思考过程）'}

你对外的说法：
{night_action['public_description'] if night_action else '未记录'}

你遇到的其他玩家：
{encounters[0]['full_description'] if encounters else '没有遇到其他玩家'}

当前游戏状态：
{game_state}

{role_prompt}

发言要求：
1. 你的发言必须与昨晚的行动记录和思考过程保持一致
2. 使用你对外的说法来解释你的行动，不要暴露真实行动
3. 如果遇到了其他玩家：
   - 描述在什么地点遇到的
   - 对方在做什么
   - 你们之间有什么互动
4. 分析和推理：
   - 基于你昨晚的观提出质疑
   - 为你的行动提供合理解释
   - 对死亡玩家提出你的看法
5. 注意事项：
   - 永远不要透露自己的真实身份
   - 不要说"作为xxx"这样的话
   - 要符合你的性格特点
   - 表现出合理的情绪和态度
   - 可以对其他人提出质疑或提问

最近的发言记录：
"""
        # 只保留最近的5条发言记录
        recent_speeches = speech_history[-5:] if speech_history else []
        for speech in recent_speeches:
            prompt += f"{speech['name']}：{speech['speech']}\n"

        prompt += "\n请根据以上信息给出一个详细的发言。记住要与你昨晚的行动和思考保持一致。"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self.ai_keys[ai_player.qq_id]}"},
                    json={
                        "model": "claude-3-sonnet-20240229",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 2000  # 增加token限制以获得更详细的发言
                    }
                ) as response:
                    result = await response.json()
                    if "choices" in result and result["choices"]:
                        speech = result["choices"][0]["message"]["content"]
                        # 清理可能的引号和多余的格式
                        speech = speech.strip('"').strip()
                        if "：" in speech:  # 如果AI回复包含了角色前缀，去掉它
                            speech = speech.split("：", 1)[1]
                        # 检查是否包含身份暴露
                        if "の" in speech :
                            # 如果发现暴露身份，使用预设的安全发言
                            speech = f"昨晚{night_action['time'] if night_action else '深夜'}的时候，我在{night_action['area'] if night_action else '四处走动'}。{night_action['public_description'] if night_action else '我们要冷静分析，仔细观察每个人的行为。'}"
                        return speech
        except Exception as e:
            print(f"AI发言生成失败：{str(e)}")
            
        return "（思考中...）"

    def find_player_by_name_or_id(self, name_or_id: str) -> Optional[Player]:
        """通过名字或ID找玩家"""
        # 先尝试通过ID查找
        if name_or_id in self.game.players:
            return self.game.players[name_or_id]
        
        # 再尝试通过名字查找
        for player in self.game.players.values():
            if player.name == name_or_id:
                return player
        return None

    def get_game_state_info(self) -> str:
        """获取当前游戏状态信息"""
        if not self.game:
            return ""
            
        info = f"游戏状态：{self.game.state.value}\n"
        info += f"当前是第{self.game.day_count}天\n"
        
        alive_players = [p for p in self.game.players.values() if not p.is_dead]
        dead_players = [p for p in self.game.players.values() if p.is_dead]
        
        info += f"存活玩家（{len(alive_players)}人）：{', '.join(p.name for p in alive_players)}\n"
        if dead_players:
            info += f"死亡玩家（{len(dead_players)}人）：{', '.join(f'{p.name}（{p.role.value}）' for p in dead_players)}\n"
        
        return info

    async def process_vote(self):
        """处理投票结果"""
        if not self.game or not self.game.voting_in_progress:
            return

        # 确保votes属性存在
        if not hasattr(self.game, 'votes'):
            self.game.votes = {}

        # 统计票数
        vote_counts = {}
        for player_id, votes in self.game.votes.items():
            if player_id not in vote_counts:
                vote_counts[player_id] = 0
            vote_counts[player_id] += len(votes) if votes else 0

        # 记录每个人的投票情况
        vote_log = "投票结果：\n"
        for player_id, votes in self.game.votes.items():
            if votes:  # 确保votes不为None
                voters = [self.game.players[v].name for v in votes]
                vote_log += f"{self.game.players[player_id].name}：{len(votes)}票（{', '.join(voters)}）\n"
        self.log_game(vote_log)
        await self.send_group_message(self.game.group_id, vote_log)

        # 处理投票结果
        if not vote_counts:
            message = "没有人投票，跳过投票环节。"
            self.log_game(message)
            await self.send_group_message(self.game.group_id, message)
        else:
            # 找出票数最多的玩家
            max_votes = max(vote_counts.values())
            most_voted = [pid for pid, votes in vote_counts.items() if votes == max_votes]

            if len(most_voted) > 1:
                message = f"票数相同，无人被处决。"
                self.log_game(message)
                await self.send_group_message(self.game.group_id, message)
            else:
                victim = self.game.players[most_voted[0]]
                victim.die("被投票处决")
                # 在日志中记录身份，但不在群里显示
                self.log_game(f"{victim.name}被投票处决，身份是{victim.role.value}")
                await self.send_group_message(self.game.group_id, f"{victim.name}被投票处决")

                # 如果是猎人，给出开枪机会
                if victim.role == Role.HUNTER:
                    message = f"猎人请使用 !lrs shoot <玩家名字> 开枪带走一名玩家"
                    self.log_game(message)
                    await self.send_group_message(self.game.group_id, message)
                    self.game.pending_death = victim.qq_id
                    # 设置30秒后自动结束开枪等待
                    asyncio.create_task(self.clear_hunter_pending(30))
                    return  # 等待猎人开枪,不立即进入夜晚

        # 检查游戏是否结束
        game_result = self.game.check_game_over()
        if game_result:
            self.game.state = GameState.ENDED
            message = f"游戏结束，{'好人' if game_result == 'villager' else '狼人'}获胜！"
            self.log_game(message)
            await self.send_group_message(self.game.group_id, message)
            return

        # 重置投票状态
        self.game.voting_in_progress = False
        self.game.votes.clear()
        self.game.speaking_order = None
        self.game.current_speaker_index = -1
        self.game.speech_history = []

        # 进入夜晚阶段
        self.game.state = GameState.NIGHT  # 直接设置状态为夜晚
        self.game.day_count += 1  # 增加天数
        
        # 重置夜晚相关状态
        self.game.werewolf_killed = None
        self.game.seer_checked = False
        self.game.witch_used_potion = False
        self.game.witch_used_poison = False
        
        # 发送夜晚开始的消息
        night_message = f"\n进入第{self.game.day_count}天夜晚...\n{self.game.current_scene['_full_data']['night_description']}\n\n"
        
        # 给活着的玩家发送提示
        alive_players = [p for p in self.game.players.values() if not p.is_dead]
        werewolves = [p for p in alive_players if p.role == Role.WEREWOLF and not p.is_ai]
        seers = [p for p in alive_players if p.role == Role.SEER and not p.is_ai]
        witches = [p for p in alive_players if p.role == Role.WITCH and not p.is_ai]
        
        if werewolves:
            night_message += "狼人请私聊使用 !lrs kill <目标> <地点> <时间> 杀人\n"
        if seers:
            night_message += "预言家请私聊使用 !lrs see <目标> 查验身份\n"
        if witches:
            night_message += "女巫请私聊使用 !lrs save 使用解药，或 !lrs poison <目标> 使用毒药\n"
            
        night_message += "\n所有玩家行动完毕后，请使用 !lrs endnight 结束夜晚"
        
        await self.send_group_message(self.game.group_id, night_message)
        
        # 处理AI玩家的夜间行动
        await self.process_ai_actions()

    async def generate_ai_status(self, ai_player: Player, prompt: str) -> str:
        """生成AI玩家的状态描述"""
        personality = ai_player.personality
        night_action = self.game.get_player_night_action(ai_player)
        
        # 获取所有死亡记录和行动记录
        death_records = []
        for player in self.game.players.values():
            if player.is_dead and player.death_reason:
                death_records.append(f"{player.name}：{player.death_reason}")
        
        # 获取最近的行动记录
        action_records = []
        for player in self.game.players.values():
            action = self.game.get_player_night_action(player)
            if action and action.get('public_description'):
                action_records.append(f"{player.name}：{action['public_description']}")
        
        prompt = f"""你是一个狼人杀游戏中的玩家。

你的身份信息：
姓名：{ai_player.name}
性别：{personality['gender']}
年龄：{personality['age']}岁
性格：{personality['personality']}
背景：{personality['background']}
行为习惯：{personality['behavior_style']}

当前场景：
{self.game.current_scene['current_scene']}

死亡记录：
{chr(10).join(death_records) if death_records else '暂无死亡记录'}

观察到的行动：
{chr(10).join(action_records) if action_records else '暂无可见行动'}

你昨晚的行动：
{night_action['public_description'] if night_action else '（没有记录）'}

请根据以上信息，用一到两句话总结当前的状况，包括：
1. 死亡玩家的情况（地点、时间、死因）
2. 你观察到的可疑行为
3. 你的个人状态

注意：不暴露你的身份，不要提到你的具体行动，只描述外在表现和观察结果。"""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self.ai_keys[ai_player.qq_id]}"},
                    json={
                        "model": "claude-3-sonnet-20240229",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 1500
                    }
                ) as response:
                    result = await response.json()
                    if "choices" in result and result["choices"]:
                        status = result["choices"][0]["message"]["content"]
                        # 清理可能的引号和多余的格式
                        status = status.strip('"').strip()
                        if "：" in status:  # 如果AI回复包含了角色前缀，去掉它
                            status = status.split("：", 1)[1]
                        return status
        except Exception as e:
            print(f"AI状态生成失败：{str(e)}")
            
        return "神色凝重地思考着昨晚发生的事情。"

    async def process_night_encounters(self):
        """处理夜间遭遇"""
        if not self.game:
            return
            
        # 获取每个区域的玩家
        area_players = {}
        for area in self.game.current_scene['areas'].keys():
            players = self.game.get_players_in_area(area)
            if len(players) > 1:
                area_players[area] = players
        
        # 处理每个区域的遭遇
        for area, players in area_players.items():
            for player in players:
                for other in players:
                    if player != other and not player.is_dead and not other.is_dead:
                        # 获取遭遇概率
                        encounter_chance = 0.3 if self.game.is_kill_location(area) else 0.8
                        
                        if random.random() < encounter_chance:
                            # 记录遭遇
                            encounter_info = self.game.get_player_night_action(other)
                            if encounter_info:
                                self.game.record_encounter(player, other, area, encounter_info)
                                self.log_game(f"[遭遇] {player.name}在{area}遇到{other.name}正在{encounter_info['action']}")

    def record_kill_info(self, killer: Player, target: Player, location: str, kill_time: str):
        """记录杀人信息"""
        if not hasattr(self, 'kill_info'):
            self.kill_info = {}
        
        self.kill_info = {
            'killer': killer.qq_id,
            'target': target.qq_id,
            'location': location,
            'time': kill_time
        }
        
        # 记录凶手的行动
        self.record_activity(killer, location, f"在{kill_time}杀死了{target.name}", 
            full_description=f"我在{location}的{kill_time}杀死了{target.name}。为了不被发现，我需要编造一个合理的理由解释我当时在做什么。")

    async def get_ai_vote_decision(self, ai_player: Player) -> Optional[Player]:
        """获取AI的投票决策"""
        game_state = self.get_game_state_info()
        personality = ai_player.personality
        
        # 获取AI的夜间行动记录和遭遇记录
        night_action = self.game.get_player_night_action(ai_player)
        encounters = self.game.get_player_encounters(ai_player)
        
        prompt = f"""你是一个狼人杀游戏中的玩家。记住：永远不要在回复中透露自己的真实身份！

你的身份信息：
姓名：{ai_player.name}
性别：{personality['gender']}
年龄：{personality['age']}岁
性格：{personality['personality']}
背景{personality['background']}
行为习惯：{personality['behavior_style']}

当前场景：
{self.game.current_scene['current_scene']}

你昨晚的行动：
地点：{night_action['area'] if night_action else '未记录'}
时间：{night_action['time'] if night_action else '未记录'}
行动：{night_action['full_description'] if night_action else '未记录'}

你遇到的其他玩家：
{encounters[0]['full_description'] if encounters else '没有遇到其他玩家'}

当前游戏状态：
{game_state}

发言记录：
"""
        # 添加最近的发言记录
        for speech in self.game.speech_history[-5:]:
            prompt += f"{speech['name']}：{speech['speech']}\n"

        prompt += """
请分析所有玩家的发言和行为，然后决定要投票给谁。考虑以下因素：
1. 玩家的发言是否有逻辑漏洞
2. 玩家的行动是否可疑
3. 其他玩家对该玩家的态度
4. 你遇到的可疑情况

请用第一人称详细描述你的分析过程，然后在最后一行给出你的投票决定，格式为：
投票给xxx 或 弃权"""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self.ai_keys[ai_player.qq_id]}"},
                    json={
                        "model": "claude-3-sonnet-20240229",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 1500  # 从500改为1500
                    }
                ) as response:
                    result = await response.json()
                    if "choices" in result and result["choices"]:
                        decision_text = result["choices"][0]["message"]["content"]
                        self.log_game(f"[AI思考] {ai_player.name}的投票分析：{decision_text}")
                        
                        # 解析投票决定
                        last_line = decision_text.strip().split('\n')[-1]
                        if "投票给" in last_line:
                            target_name = last_line.split("投票给")[-1].strip()
                            target = self.find_player_by_name_or_id(target_name)
                            if target and not target.is_dead:
                                return target
                        
        except Exception as e:
            print(f"AI投票决策失败：{str(e)}")
            self.log_game(f"AI投票决策失败：{str(e)}")
        
        return None

    def check_game_over(self) -> Optional[str]:
        """检查游戏是否结束
        返回：
        - 'villager' 表示好人胜利
        - 'werewolf' 表示狼人胜利
        - None 表示游戏继续
        """
        # 第4天白天开始时，好人自动胜利
        if self.day_count >= 4 and self.state == GameState.DAY:
            return 'villager'

        # 计算存活玩家
        alive_players = [p for p in self.players.values() if not p.is_dead]
        werewolves = [p for p in alive_players if p.role == Role.WEREWOLF]
        villagers = [p for p in alive_players if p.role != Role.WEREWOLF]

        # 所有狼人死亡，好人胜利
        if not werewolves:
            return 'villager'
        # 狼人数量大于等于好人，狼人胜利
        elif len(werewolves) >= len(villagers):
            return 'werewolf'
        return None

@register(
    name="狼人杀",
    description="狼人杀游戏插件",
    version="1.0.0",
    author="Cursor"
)
class WerewolfPlugin(BasePlugin):
    def __init__(self, host: PluginHost):
        super().__init__(host)
        self.operator = WerewolfOperator(host)
        self.operator.plugin = self
        self.current_context = None

    @handler(GroupNormalMessageReceived)
    async def on_group_message(self, ctx: EventContext):
        text = ctx.event.text_message.strip()
        if text.startswith(("!lrs", "！lrs")):
            # 保存当前上下文
            self.current_context = ctx
            # 移除命令前缀并分割数
            parts = text[4:].strip().split()
            # 创建执行上下文
            exec_context = entities.ExecuteContext(
                query=ctx.event,
                crt_params=parts
            )
            # 执行命令
            async for result in self.operator.execute(exec_context):
                ctx.add_return("reply", [Plain(text=result.text)])
            ctx.prevent_default()

    async def send_group_message(self, group_id: str, text: str):
        """发送群消息"""
        if self.current_context:
            self.current_context.add_return("reply", [Plain(text=text)])

    async def send_private_message(self, user_id: str, text: str):
        """发送私聊消息"""
        if self.current_context:
            self.current_context.add_return("reply", [Plain(text=text)])

    def __del__(self):
        pass

