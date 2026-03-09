# LLM 插件感知增强插件

使 LLM 可以知道有哪些插件指令，以及知道插件触发的消息内容，以此解决某些调用问题。

## 功能特性

### LLM Tools

#### 1. `get_available_commands`
获取当前可用的插件指令列表。当用户询问有哪些指令、可以使用什么命令、如何使用插件时，LLM 会自动调用此工具。

**参数：**
- `plugin_name` (可选): 指定插件名称，不填则返回所有插件的指令

**示例对话：**
```
用户: 有哪些指令可以用？
LLM: [调用 get_available_commands] 让我为您查询可用的指令...
```

#### 2. `get_plugin_info`
获取插件的详细信息。当用户想了解某个插件的功能、版本、作者等信息时，LLM 会自动调用此工具。

**参数：**
- `plugin_name` (可选): 插件名称，不填则返回所有已加载插件的列表

**示例对话：**
```
用户: 天气插件是做什么的？
LLM: [调用 get_plugin_info(plugin_name="weather")] 让我为您查询天气插件的信息...
```

### 事件监听

- **`on_using_llm_tool`**: 监听 LLM Tool 调用事件，记录工具调用信息
- **`on_llm_tool_respond`**: 监听 LLM Tool 响应事件，记录工具返回结果

### 指令

- `/plugin_tools`: 查看插件工具调用历史
- `/list_commands`: 列出所有可用指令

## 配置项

在 `_conf_schema.json` 中定义了以下配置项：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enable_command_tool` | boolean | true | 是否启用指令查询工具 |
| `enable_plugin_info_tool` | boolean | true | 是否启用插件信息查询工具 |
| `enable_tool_logging` | boolean | true | 是否记录工具调用日志 |
| `log_level` | string | "info" | 日志级别 (info/debug) |

## 使用场景

### 场景 1: 用户询问可用指令
```
用户: 这个机器人能做什么？
LLM: [自动调用 get_available_commands] 
这个机器人支持以下功能：
- /天气: 查询天气信息
- /翻译: 翻译文本
- /搜索: 搜索网络内容
...
```

### 场景 2: 用户想了解特定插件
```
用户: 算卦插件怎么用？
LLM: [自动调用 get_plugin_info(plugin_name="suangua")]
算卦插件是一个传统金钱卦起卦法插件，版本 1.0.0，作者 86lbs。
它提供了以下指令：
- /算卦: 进行金钱卦起卦
```

### 场景 3: 调试工具调用问题
```
用户: /plugin_tools
机器人: 
## 工具调用历史 (最近20条)
📞 调用 `get_available_commands` 参数: {}
   ↳ 返回: ## 可用指令列表...
📞 调用 `get_weather` 参数: {"city": "北京"}
   ↳ 返回: 北京今天天气晴朗...
```

## 安装

1. 将插件文件夹放入 AstrBot 的 `data/plugins/` 目录
2. 重启 AstrBot 或在管理面板中激活插件

## 致谢

本插件使用 [AstrBot 插件开发指南](https://github.com/86lbs/astrbot_plugin_dev_guide) 开发。

## 许可证

MIT License
