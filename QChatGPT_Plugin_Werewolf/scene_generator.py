import random
import aiohttp

# 天气系统
WEATHER_CONDITIONS = {
    "晴朗": {
        "day": "阳光明媚，天空湛蓝，偶有白云飘过。",
        "night": "夜空清澈，繁星点点，圆月高悬，洒下皎洁的银辉。"
    },
    "多云": {
        "day": "云层时厚时薄，太阳若隐若现，在地面投下斑驳的光影。",
        "night": "厚重的云层遮住了天空，显得格外昏暗，让人心生不安。"
    },
    "小雨": {
        "day": "细雨绵绵，空气中弥漫着潮湿的气息，雨丝在微风中轻轻飘荡。",
        "night": "夜雨淅沥，雨滴敲打着窗户，发出轻柔的声响，远处偶尔传来几声蛙鸣。"
    },
    "暴雨": {
        "day": "大雨倾盆，雷声轰鸣，闪电划破天际，狂风呼啸而过。",
        "night": "狂风骤雨，电闪雷鸣，暴雨击打着建筑发出震耳欲聋的声响，黑暗中时而被闪电照亮。"
    },
    "雾": {
        "day": "浓雾弥漫，能见度极低，周围的景物都笼罩在一片朦胧之中。",
        "night": "夜晚的浓雾更显诡异，雾气在微弱的光线下流动，仿佛隐藏着什么。"
    }
}

# 玩家名字生成
NAMES = [
    "月华", "星璃", "雨霖", "雪瑶", "风铃", "云裳", "晓梦", "夜阑", 
    "阳煦", "雷音", "霜华", "雾语", "光辉", "影姿", "梦兰", "幻翎",
    "清韵", "墨凝", "紫萱", "沐晴", "流苏", "若溪", "澜雅", "芷若",
    "千寻", "暮色", "凌波", "听雨", "飞雪", "映月", "书兰", "问雁"
]

def generate_player_name():
    """生成一个随机的优美玩家名字"""
    return random.choice(NAMES)

async def get_game_status_summary(game_state: dict) -> str:
    """获取游戏状态的详细总结"""
    api_key = "hk-yp8t301000040760f637db2c86cdefc87b4e9c61cbbf803a"
    
    # 构建状态信息
    status_info = {
        "场景信息": {
            "名称": game_state["name"],
            "当前天气": game_state["weather"],
            "时间": "白天" if game_state.get("is_day", False) else "夜晚",
            "场景变化": game_state.get("scene_changes", {}),  # 记录场景中的物品变化
            "区域状态": game_state.get("area_status", {})    # 记录各区域的特殊状态
        },
        "玩家信息": {
            "存活玩家": game_state.get("alive_players", []),
            "死亡玩家": game_state.get("dead_players", []),
            "玩家位置": game_state.get("player_locations", {}),  # 记录玩家所在区域
            "玩家状态": game_state.get("player_status", {})     # 记录玩家的特殊状态
        },
        "游戏进程": {
            "当前阶段": game_state.get("game_phase", "未开始"),
            "昨夜事件": game_state.get("last_night_events", []),
            "重要事件": game_state.get("important_events", [])
        }
    }
    
    prompt = f"""作为狼人杀游戏的旁白，请根据以下信息生成一段简洁但富有氛围感的游戏状态描述：

{status_info}

要求：
1. 重点描述场景和环境的变化（如果有）
2. 描述玩家们的状态和位置
3. 提及重要事件的影响
4. 营造紧张的氛围
5. 不要暴露任何玩家身份
6. 使用优美但简洁的语言

格式：
【环境概况】
- 天气和时间
- 场景变化
- 特殊状态

【人物动向】
- 玩家分布
- 人物状态

【重要事件】
- 关键事件回顾（如果有）
"""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai-hk.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "claude-3-sonnet-20240229",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 700
                }
            ) as response:
                result = await response.json()
                if "choices" in result and result["choices"]:
                    return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"获取状态总结失败：{str(e)}")
        return "获取游戏状态失败..."

# 场景背景故事
SCENE_STORIES = {
    "神秘村庄": "一个与世隔绝的古老村庄，因为一个古老的预言，村民们必须在每个月圆之夜进行一场审判仪式。然而，这个看似平静的村庄却暗藏杀机...",
    "古堡": "这座历史悠久的古堡举办了一场神秘的化妆舞会，宾客们戴着精美的面具尽情狂欢。但随着午夜钟声的敲响，一场致命的游戏悄开始...",
    "豪华旅馆": "一场突如其来的暴风雪让这家偏僻山区的豪华旅馆与外界失去了联系。被困的旅客们很快发现，他们中间潜伏着一些可怕的秘密...",
    "废弃学校": "传说这所废弃多年的学校曾发生过一件离奇的命案。一群探险者在一个雨夜闯入校园，却意外卷入了一场生死游戏...",
    "豪华邮轮": "这艘豪华邮轮正在进行它的处女航，船上举办着盛大的晚宴。然而就在海上狂欢正酣时，一连诡异的事件开始发生..."
}

SCENES = [
    {
        "name": "神秘村庄",
        "day_description": "阳光照射在村庄的木屋上，村民们三三两两地在村口闲聊。古老的水井边围着几个打水的村民，远处的麦田金黄一片。",
        "night_description": "月黑风高的深夜，村庄笼罩在浓雾之中。古老的木屋散落在村子各处，昏黄的灯光透过窗户洒在泥泞的小路上。",
        "areas": {
            "村口广场": "村子的中心广场，有一口古老的水井和几张石凳。夜晚时这里通常很安静，能听到风吹过的声音。",
            "谷仓": "一座破旧的木制谷仓，堆满了干草和农具。黑暗中传来老鼠窸窸窣窣的声音。",
            "教堂": "村子里唯一的石建筑，哥特式的尖顶在月光下显得格外阴森。教堂的钟声每隔一小时都会响起。",
            "民居区": "几排木质平房，烟囱里飘出炊烟。窗户后时不时能看到人影晃动。",
            "小树林": "村子边缘的一片树林，枝叶茂密，月光难以穿透。时常传来猫头鹰的叫声。"
        }
    },
    {
        "name": "古堡",
        "day_description": "阳光透过彩绘玻璃窗投射在古堡的大理石地板上，形成斑驳的光影。城堡的仆人们正在打扫卫生，庭院里传来鸟儿的鸣叫声。",
        "night_description": "夜幕降临，古堡内的烛光摇曳，在墙壁上投下诡异的影子。走廊上挂着的盔甲在月光下泛着冷光，仿佛随时会活过来。",
        "areas": {
            "大厅": "城堡的中央大厅，天花板很高，挂着巨大的枝形吊灯。墙上挂着历代城主的肖像画，他们的目光似乎在注视着每个人。",
            "图书室": "堆满了古籍的房间，空气中弥漫着旧书的气味。角落里有一张红木书桌和一把摇椅，书架上布满蜘蛛网。",
            "地下室": "阴冷潮湿的地下空间，墙上挂着火把。有几个木桶和架子，角落里堆着一些神秘的箱子。",
            "塔楼": "城堡最高处的房间，能俯瞰整个山谷。有一个天文望远镜和一些奇怪的观测仪器。",
            "庭院": "被城堡环绕的内院，种着一些枯萎的花草。中央有一口干涸的喷泉，四周摆着长满青苔的石椅。"
        }
    },
    {
        "name": "豪华旅馆",
        "day_description": "阳光透过落地窗照进旅馆大堂，水晶吊灯折射出璀璨的光芒。人们在餐厅享用早餐，服务员忙碌地穿梭其间。",
        "night_description": "夜深人静，旅馆的走廊上只剩下应急灯的微光。厚重的地毯吸收了所有脚步声，偶尔能听到房间里传出的细微响动。",
        "areas": {
            "大堂": "装修豪华的接待大厅，铺着红色地毯。前台后面挂着一排房间钥匙，墙上的时钟滴答作响。",
            "餐厅": "宽敞的用餐区域，摆放着圆形餐桌。餐具反射着柔和的灯光，空气中飘着食物的香气。",
            "休息室": "舒适的会客区，有几张皮质沙发和茶几。角落里放着一架老式钢琴。",
            "走廊": "铺着厚重地毯的客房走廊，两侧是一扇扇紧闭的房门。墙上的壁灯投下昏黄的光。",
            "天台": "旅馆顶层的露台，可以看到远处的城市夜景。四周装着铁栏杆，地上摆着几张躺椅。"
        }
    },
    {
        "name": "废弃学校",
        "day_description": "阳光透过破碎的窗户照进空荡荡的教室，照亮了空中飘浮的灰尘。操场上长满了杂草，秋千在风中轻轻摇晃。",
        "night_description": "月光给废弃的校园蒙上一层银纱，空旷的走廊回荡着风声。教室里的课桌椅投下长长的影子，黑板上依稀可见粉笔的痕迹。",
        "areas": {
            "教室": "一间废弃的教室，课桌椅东倒西歪。黑板上还留着未擦除的字迹，墙上挂着斑驳的教学图片。",
            "图书馆": "布满灰尘的图书馆，书架上的书籍已经发黄。破损的桌椅散落各处，角落里有几台老旧的电脑。",
            "体育馆": "空荡荡的体育馆，木质地板已经翘起。墙上挂着褪色的校旗，看台上堆着一些体育器材。",
            "实验室": "杂乱的化学实验室，试管和烧杯倒在实验台上。药品柜的玻璃碎裂，空气中有股奇怪的味道。",
            "天台": "学校最高处的天台，围栏已经生锈。地上散落着几把折叠椅，可以看到整个校园的全景。"
        }
    },
    {
        "name": "豪华邮轮",
        "day_description": "阳光洒在波光粼粼的海面上，海鸥在船舷附近盘旋。游客们在甲板上晒太阳，享受着海风的轻抚。远处偶尔能看到跃出水面的海豚。",
        "night_description": "幕笼罩着无边的大海，邮轮的灯光在漆黑的海面上倒映出长长的光带。甲板上传来轻柔的音乐声，海风中夹杂着咸咸的海水气息。",
        "areas": {
            "观景甲板": "邮轮最上层的露天甲板，铺着柚木地板。四周是透明的玻璃护墙，摆放着许多躺椅。夜晚能看到满天繁星倒映在海面上。",
            "舞会大厅": "金碧辉煌的大型舞厅，水晶吊灯闪烁着柔和的光芒。舞池周围摆放着圆形餐桌，舞台上的乐器安静地等待着演奏者。",
            "船长室": "位于船头的指挥中心，墙上挂满了航海仪器和海图。宽大的落地窗能将海面尽收眼底，操控台上的仪表发出微弱的光。",
            "豪华套房": "装修考究的客房区域，走廊两侧是一扇扇雕花木门。厚重的地毯吸收了所有脚步声，墙上的壁灯散发着温暖的光。",
            "机械舱": "位于船底的机械区域，充满了管道和仪表。发动机的轰鸣声在这里格外清晰，闷热的空气中弥漫着机油的气味。"
        }
    }
]

async def get_random_scene() -> dict:
    """获取随机场景"""
    scene = random.choice(SCENES)
    weather = random.choice(list(WEATHER_CONDITIONS.keys()))
    weather_desc = WEATHER_CONDITIONS[weather]
    story = SCENE_STORIES[scene["name"]]
    
    # 根据天气调整描述
    night_desc = f"{weather_desc['night']}\n{scene['night_description']}"
    
    # 返回简化的场景信息
    return {
        "name": scene["name"],
        "story": story,
        "weather": weather,
        "current_scene": night_desc,
        "areas": scene["areas"],
        # 以下字段仅供内部使用
        "_full_data": {
            "day_description": f"{weather_desc['day']}\n{scene['day_description']}",
            "night_description": night_desc,
            "scene_changes": {},
            "area_status": {}
        }
    }

async def get_ai_behavior_report(ai_player: dict, game_state: dict, is_day: bool) -> str:
    """获取AI玩家的行为报告"""
    api_key = ""
    
    # 构建状态信息
    player_info = {
        "玩家信息": {
            "名字": ai_player["name"],
            "身份": ai_player["role"],  # AI内部知道自己的身份
            "状态": ai_player.get("status", "正常"),
            "当前位置": ai_player.get("current_location", "未知"),
            "可用区域": game_state["areas"]
        },
        "环境信息": {
            "场景": game_state["name"],
            "天气": game_state["weather"],
            "时间": "白天" if is_day else "夜晚",
            "场景描述": game_state["day_description"] if is_day else game_state["night_description"]
        },
        "游戏信息": {
            "存活玩家": game_state.get("alive_players", []),
            "死亡玩家": game_state.get("dead_players", []),
            "上一轮事件": game_state.get("last_events", [])
        }
    }
    
    prompt = f"""作为一个狼人杀游戏中的玩家，请根据以下信息描述你的行为和状态：

{player_info}

要求：
1. 描述你当前的位置和行动
2. 说明你观察到的情况
3. 描述你的心理状态
4. 不要暴露你的真实身份
5. 符合你的性格特点

请用以下固定格式回复：

【位置】
我现在在xxx（具体区域名称）

【行动】
- 正在做什么
- 观察到什么
- 有什么想法

【状态】
- 身体状态
- 心理状态
- 对当前局势的看法

【备注】
其他需要补充的信息（如果有）
"""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai-hk.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "claude-3-sonnet-20240229",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 350
                }
            ) as response:
                result = await response.json()
                if "choices" in result and result["choices"]:
                    return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"获取AI行为报告失败：{str(e)}")
        return f"{ai_player['name']}当前无法行动..."

async def get_all_ai_reports(game_state: dict, is_day: bool) -> list:
    """获取所有AI玩家的行为报告"""
    reports = []
    ai_players = [p for p in game_state.get("alive_players", []) if p.get("is_ai", False)]
    
    for ai_player in ai_players:
        report = await get_ai_behavior_report(ai_player, game_state, is_day)
        reports.append({
            "name": ai_player["name"],
            "report": report
        })
        # 更新玩家位置和状态
        if "【位置】" in report:
            location = report.split("【位置】")[1].split("\n")[1].strip()
            ai_player["current_location"] = location
    
    return reports

def format_game_start_message(scene: dict) -> str:
    """格式化游戏开始消息"""
    message = [
        "🎭 游戏创建成功！",
        f"\n【场景】{scene['name']}",
        f"\n【背景】{scene['story']}",
        f"\n【天气】{scene['weather']}",
        f"\n【当前场景】\n{scene['current_scene']}",
        "\n【探索区域】"
    ]
    
    for area_name, area_desc in scene['areas'].items():
        message.append(f"\n• {area_name}：{area_desc}")
    
    message.append("\n\n💫 请使用 !lrs join 加入游戏")
    
    return "".join(message)
