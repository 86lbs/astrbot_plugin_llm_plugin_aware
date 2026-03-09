# 更新日志

## [1.0.0] - 2025-03-09

### Added
- 初始版本发布
- 新增 LLM Tool `get_available_commands`: 让 LLM 可以查询当前可用的所有插件指令
- 新增 LLM Tool `get_plugin_info`: 让 LLM 可以获取指定插件的详细信息
- 新增事件监听 `on_using_llm_tool`: 监听 LLM Tool 调用事件，记录工具调用信息
- 新增事件监听 `on_llm_tool_respond`: 监听 LLM Tool 响应事件，记录工具返回结果
- 新增指令 `/plugin_tools`: 查看插件工具调用历史
- 新增指令 `/list_commands`: 列出所有可用指令
- 新增配置项支持:
  - `enable_command_tool`: 是否启用指令查询工具
  - `enable_plugin_info_tool`: 是否启用插件信息查询工具
  - `enable_tool_logging`: 是否记录工具调用日志
  - `log_level`: 日志级别

### Changed
- 无

### Fixed
- 无
