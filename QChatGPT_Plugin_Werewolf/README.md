# AI狼人杀游戏插件

这是一个支持AI玩家参与的狼人杀游戏插件。

## 功能特性

- 支持真实玩家和AI玩家混合游戏
- 使用GPT-4生成游戏场景和AI玩家对话
- 支持多种角色：狼人、村民、预言家、女巫、猎人
- 支持6-12人游戏
- 自动补充AI玩家

## 命令列表

1. 创建游戏：
```
！lrs
```

2. 加入游戏：
```
！jr
```

3. 开始游戏（用AI补充剩余位置）：
```
！lrss
```

4. 投票：
```
！tp <qq号>
```

5. 预言家查验：
```
！yy <qq号>
```

6. 女巫救人/毒人：
```
！nw <qq号>
```

7. 猎人开枪：
```
！lr <qq号>
```

## 配置说明

配置文件位于 `config.json`，格式如下：

```json
{
  "min_players": 6,
  "max_players": 12,
  "role_config": {
    "6": {"WEREWOLF": 2, "VILLAGER": 2, "SEER": 1, "WITCH": 1},
    "7": {"WEREWOLF": 2, "VILLAGER": 3, "SEER": 1, "WITCH": 1},
    "8": {"WEREWOLF": 3, "VILLAGER": 3, "SEER": 1, "WITCH": 1},
    "9": {"WEREWOLF": 3, "VILLAGER": 4, "SEER": 1, "WITCH": 1},
    "10": {"WEREWOLF": 3, "VILLAGER": 4, "SEER": 1, "WITCH": 1, "HUNTER": 1}
  }
}
```

## 游戏流程

1. 使用 `！lrs` 创建新游戏
2. 玩家使用 `！jr` 加入游戏
3. 使用 `！lrss` 开始游戏，系统会用AI玩家补充剩余位置
4. 游戏开始后，系统会分配角色并私聊告知每个玩家
5. 按照狼人杀正常流程进行游戏：
   - 夜晚：狼人杀人、预言家查验、女巫救人/毒人
   - 白天：玩家讨论、投票处决

## 注意事项

1. 游戏需要至少6名玩家才能开始
2. AI玩家会根据自己的角色和场上形势做出合理的判断和行动
3. 每个玩家的角色和行动都是保密的
4. 死亡的玩家不能发言和使用技能

## 安装说明

1. 将插件文件夹放入 `plugins` 目录
2. 安装必要依赖：
```bash
pip install aiohttp
```
3. 确保目录结构如下：
```
plugins/
  └── QChatGPT_Plugin_Werewolf/
      ├── main.py
      ├── config.json
      ├── __init__.py
      └── README.md
```

## 更新日志

### v0.1
- 初始版本发布
- 基本的狼人杀游戏功能
- 支持AI玩家
- 支持多种角色 