"""
LLM 插件感知增强插件

使 LLM 可以知道有哪些插件指令，以及知道插件触发的消息内容，以此解决某些调用问题。

功能：
1. 提供 LLM Tool 让 LLM 查询可用的插件指令
2. 提供 LLM Tool 让 LLM 获取插件详细信息
3. 监听 LLM Tool 调用事件，记录工具调用信息
4. 监听 LLM Tool 响应事件，记录工具返回结果
"""

from astrbot.api import star, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.star.star_handler import star_handlers_registry, EventType
from astrbot.core.star.filter.command import CommandFilter
from astrbot.core.agent.tool import FunctionTool
from typing import Any
import json


class LLMPluginAware(star.Star):
    """LLM 插件感知增强插件类"""

    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self._config = config or {}
        
        # 配置项
        self.enable_command_tool = self._config.get("enable_command_tool", True)
        self.enable_plugin_info_tool = self._config.get("enable_plugin_info_tool", True)
        self.enable_tool_logging = self._config.get("enable_tool_logging", True)
        self.log_level = self._config.get("log_level", "info")
        
        # 工具调用记录
        self._tool_call_history: list[dict] = []

    async def initialize(self):
        """插件初始化"""
        logger.info("LLM 插件感知增强插件初始化完成")
        logger.info(f"配置: enable_command_tool={self.enable_command_tool}, "
                   f"enable_plugin_info_tool={self.enable_plugin_info_tool}, "
                   f"enable_tool_logging={self.enable_tool_logging}")

    def _log(self, message: str, level: str = "info"):
        """根据配置的日志级别输出日志"""
        if self.log_level == "debug" or level == "info":
            logger.info(message)
        elif level == "debug":
            logger.debug(message)

    def _get_all_commands(self) -> list[dict]:
        """获取所有已注册的指令"""
        commands = []
        
        for handler_md in star_handlers_registry:
            if handler_md.event_type != EventType.AdapterMessageEvent:
                continue
                
            # 查找 CommandFilter
            for event_filter in handler_md.event_filters:
                if isinstance(event_filter, CommandFilter):
                    cmd_info = {
                        "command": event_filter.command_name,
                        "alias": list(event_filter.alias) if event_filter.alias else [],
                        "description": handler_md.desc or "无描述",
                        "handler_name": handler_md.handler_name,
                        "plugin_module": handler_md.handler_module_path,
                    }
                    
                    # 获取插件名称
                    plugin = self.context.get_registered_star(handler_md.handler_module_path.split(".")[0] if "." in handler_md.handler_module_path else handler_md.handler_module_path)
                    if plugin:
                        cmd_info["plugin_name"] = plugin.name or "未知"
                        cmd_info["plugin_desc"] = plugin.desc or ""
                    else:
                        # 尝试从 star_map 获取
                        from astrbot.core.star.star import star_map
                        for module_path, metadata in star_map.items():
                            if handler_md.handler_module_path.startswith(module_path.split(".")[0] if "." in module_path else module_path):
                                cmd_info["plugin_name"] = metadata.name or "未知"
                                cmd_info["plugin_desc"] = metadata.desc or ""
                                break
                        else:
                            cmd_info["plugin_name"] = "内置"
                            cmd_info["plugin_desc"] = "AstrBot 内置功能"
                    
                    commands.append(cmd_info)
        
        return commands

    def _get_plugin_info(self, plugin_name: str) -> dict | None:
        """获取指定插件的详细信息"""
        # 首先尝试直接获取
        plugin = self.context.get_registered_star(plugin_name)
        
        if not plugin:
            # 尝试遍历所有插件查找
            all_stars = self.context.get_all_stars()
            for star in all_stars:
                if star.name and (star.name.lower() == plugin_name.lower() or 
                                  star.name.lower().replace("_", "") == plugin_name.lower().replace("_", "")):
                    plugin = star
                    break
        
        if not plugin:
            return None
        
        # 获取插件注册的 Handler
        handlers = []
        for handler_md in star_handlers_registry:
            if handler_md.handler_module_path and plugin.module_path:
                if handler_md.handler_module_path.startswith(plugin.module_path.split(".")[0] if "." in plugin.module_path else plugin.module_path):
                    handler_info = {
                        "name": handler_md.handler_name,
                        "type": handler_md.event_type.name,
                        "description": handler_md.desc or "无描述",
                    }
                    
                    # 如果是指令，获取指令名
                    for event_filter in handler_md.event_filters:
                        if isinstance(event_filter, CommandFilter):
                            handler_info["command"] = event_filter.command_name
                            if event_filter.alias:
                                handler_info["alias"] = list(event_filter.alias)
                    
                    handlers.append(handler_info)
        
        return {
            "name": plugin.name,
            "author": plugin.author,
            "description": plugin.desc,
            "version": plugin.version,
            "repo": plugin.repo,
            "activated": plugin.activated,
            "handlers_count": len(handlers),
            "handlers": handlers[:10],  # 最多返回10个handler，避免信息过多
        }

    def _get_all_plugins(self) -> list[dict]:
        """获取所有已加载的插件列表"""
        plugins = []
        all_stars = self.context.get_all_stars()
        
        for star in all_stars:
            plugin_info = {
                "name": star.name,
                "author": star.author,
                "description": star.desc,
                "version": star.version,
                "activated": star.activated,
            }
            plugins.append(plugin_info)
        
        return plugins

    @filter.llm_tool(name="get_available_commands")
    async def get_available_commands(self, event: AstrMessageEvent, plugin_name: str = "") -> str:
        '''获取当前可用的插件指令列表。当用户询问有哪些指令、可以使用什么命令、如何使用插件时调用此工具。

        Args:
            plugin_name(string): 可选，指定插件名称。如果不填则返回所有插件的指令。
        '''
        if not self.enable_command_tool:
            return "指令查询功能已禁用。"
        
        self._log(f"[LLM Tool] get_available_commands 被调用, plugin_name={plugin_name}")
        
        commands = self._get_all_commands()
        
        if plugin_name:
            # 过滤指定插件的指令
            commands = [cmd for cmd in commands if cmd.get("plugin_name", "").lower() == plugin_name.lower() 
                       or cmd.get("plugin_name", "").lower().replace("_", "") == plugin_name.lower().replace("_", "")]
        
        if not commands:
            if plugin_name:
                return f"未找到插件 '{plugin_name}' 的指令。请使用 get_plugin_info 工具查看可用插件列表。"
            return "当前没有可用的指令。"
        
        # 格式化输出
        result_lines = ["## 可用指令列表\n"]
        
        # 按插件分组
        plugins_commands = {}
        for cmd in commands:
            pn = cmd.get("plugin_name", "其他")
            if pn not in plugins_commands:
                plugins_commands[pn] = []
            plugins_commands[pn].append(cmd)
        
        for pn, cmds in plugins_commands.items():
            result_lines.append(f"### {pn}")
            for cmd in cmds:
                alias_str = f" (别名: {', '.join(cmd['alias'])})" if cmd['alias'] else ""
                result_lines.append(f"- `/{cmd['command']}`{alias_str}: {cmd['description']}")
            result_lines.append("")
        
        return "\n".join(result_lines)

    @filter.llm_tool(name="get_plugin_info")
    async def get_plugin_info_tool(self, event: AstrMessageEvent, plugin_name: str = "") -> str:
        '''获取插件的详细信息。当用户想了解某个插件的功能、版本、作者等信息时调用此工具。不填 plugin_name 则返回所有插件列表。

        Args:
            plugin_name(string): 可选，插件名称。如果不填则返回所有已加载插件的列表。
        '''
        if not self.enable_plugin_info_tool:
            return "插件信息查询功能已禁用。"
        
        self._log(f"[LLM Tool] get_plugin_info 被调用, plugin_name={plugin_name}")
        
        if not plugin_name:
            # 返回所有插件列表
            plugins = self._get_all_plugins()
            if not plugins:
                return "当前没有已加载的插件。"
            
            result_lines = ["## 已加载插件列表\n"]
            for p in plugins:
                status = "✅ 已激活" if p['activated'] else "❌ 未激活"
                result_lines.append(f"- **{p['name']}** (v{p['version'] or '未知'}) by {p['author'] or '未知'} - {status}")
                if p['description']:
                    result_lines.append(f"  {p['description']}")
            
            return "\n".join(result_lines)
        
        # 返回指定插件信息
        plugin_info = self._get_plugin_info(plugin_name)
        
        if not plugin_info:
            return f"未找到插件 '{plugin_name}'。请使用此工具（不填参数）查看所有可用插件列表。"
        
        result_lines = [
            f"## 插件信息: {plugin_info['name']}\n",
            f"- **作者**: {plugin_info['author'] or '未知'}",
            f"- **版本**: {plugin_info['version'] or '未知'}",
            f"- **描述**: {plugin_info['description'] or '无'}",
            f"- **状态**: {'✅ 已激活' if plugin_info['activated'] else '❌ 未激活'}",
            f"- **仓库**: {plugin_info['repo'] or '无'}",
            f"- **注册的处理器数量**: {plugin_info['handlers_count']}",
        ]
        
        if plugin_info['handlers']:
            result_lines.append("\n### 处理器列表")
            for h in plugin_info['handlers'][:5]:
                cmd_str = f" (指令: /{h['command']})" if 'command' in h else ""
                result_lines.append(f"- {h['name']}{cmd_str}: {h['description']}")
            if len(plugin_info['handlers']) > 5:
                result_lines.append(f"  ... 还有 {len(plugin_info['handlers']) - 5} 个处理器")
        
        return "\n".join(result_lines)

    @filter.on_using_llm_tool()
    async def on_using_llm_tool(self, event: AstrMessageEvent, tool: FunctionTool, tool_args: dict | None):
        """监听 LLM Tool 调用事件"""
        if not self.enable_tool_logging:
            return
        
        tool_info = {
            "event": "tool_call_start",
            "tool_name": tool.name if tool else "unknown",
            "tool_args": tool_args,
            "message_str": event.message_str[:200] if event.message_str else "",
            "sender_id": event.get_sender_id(),
            "sender_name": event.get_sender_name(),
        }
        
        self._tool_call_history.append(tool_info)
        
        # 保持历史记录在合理范围内
        if len(self._tool_call_history) > 100:
            self._tool_call_history = self._tool_call_history[-50:]
        
        self._log(f"[Tool Call] 工具 '{tool.name}' 被调用, 参数: {json.dumps(tool_args, ensure_ascii=False) if tool_args else '无'}")

    @filter.on_llm_tool_respond()
    async def on_llm_tool_respond(self, event: AstrMessageEvent, tool: FunctionTool, tool_args: dict | None, tool_result: Any):
        """监听 LLM Tool 响应事件"""
        if not self.enable_tool_logging:
            return
        
        # 处理 tool_result
        result_str = ""
        if tool_result:
            try:
                if hasattr(tool_result, 'content'):
                    result_str = str(tool_result.content)[:500]
                elif hasattr(tool_result, '__dict__'):
                    result_str = json.dumps(tool_result.__dict__, ensure_ascii=False, default=str)[:500]
                else:
                    result_str = str(tool_result)[:500]
            except Exception as e:
                result_str = f"<无法序列化: {e}>"
        
        tool_info = {
            "event": "tool_call_end",
            "tool_name": tool.name if tool else "unknown",
            "tool_args": tool_args,
            "tool_result": result_str,
        }
        
        self._tool_call_history.append(tool_info)
        
        self._log(f"[Tool Respond] 工具 '{tool.name}' 返回结果: {result_str[:200] if result_str else '空'}")

    @filter.command("plugin_tools")
    async def plugin_tools_command(self, event: AstrMessageEvent):
        """查看插件工具调用历史"""
        if not self._tool_call_history:
            event.set_result(
                event.plain_result("暂无工具调用历史记录。")
            )
            return
        
        history_lines = ["## 工具调用历史 (最近20条)\n"]
        for record in self._tool_call_history[-20:]:
            if record['event'] == 'tool_call_start':
                args_str = json.dumps(record['tool_args'], ensure_ascii=False) if record['tool_args'] else '无'
                history_lines.append(f"📞 调用 `{record['tool_name']}` 参数: {args_str}")
            else:
                result_str = record.get('tool_result', '无')[:100]
                history_lines.append(f"   ↳ 返回: {result_str}")
        
        event.set_result(
            event.plain_result("\n".join(history_lines))
        )

    @filter.command("list_commands")
    async def list_commands_command(self, event: AstrMessageEvent):
        """列出所有可用指令"""
        commands = self._get_all_commands()
        
        if not commands:
            event.set_result(
                event.plain_result("当前没有可用的指令。")
            )
            return
        
        result_lines = ["## 可用指令列表\n"]
        
        # 按插件分组
        plugins_commands = {}
        for cmd in commands:
            pn = cmd.get("plugin_name", "其他")
            if pn not in plugins_commands:
                plugins_commands[pn] = []
            plugins_commands[pn].append(cmd)
        
        for pn, cmds in plugins_commands.items():
            result_lines.append(f"### {pn}")
            for cmd in cmds:
                alias_str = f" (别名: {', '.join(cmd['alias'])})" if cmd['alias'] else ""
                result_lines.append(f"- `/{cmd['command']}`{alias_str}: {cmd['description']}")
        
        event.set_result(
            event.plain_result("\n".join(result_lines))
        )

    async def terminate(self):
        """插件销毁"""
        logger.info("LLM 插件感知增强插件已卸载")
