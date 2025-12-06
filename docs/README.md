# DataAgent 文档

DataAgent 是基于 DeepAgent 构建的数据智能助手平台，支持终端 CLI 和 Web 服务两种交互方式。

## 文档结构

| 文档 | 说明 |
|------|------|
| [快速开始](./getting-started.md) | 安装、配置、运行指南 |
| [架构概览](./architecture.md) | 系统架构和组件说明 |
| [开发人员手册](./developer-guide.md) | 开发环境搭建、代码规范、贡献指南 |
| [API 参考](./api-reference.md) | REST API 和 WebSocket 协议文档 |

## 详细设计文档

详细的需求、设计和实现任务请参考：
- `.kiro/specs/dataagent-development-specs/requirements.md` - 需求文档
- `.kiro/specs/dataagent-development-specs/design.md` - 设计文档
- `.kiro/specs/dataagent-development-specs/tasks.md` - 实现任务

## 项目组件

```
libs/
├── dataagent-core/      # 核心库 - Agent 引擎、事件系统、中间件
├── dataagent-cli/       # CLI 客户端 - 终端交互界面
├── dataagent-server/    # Web 服务 - REST API 和 WebSocket
├── dataagent-harbor/    # 测试框架 - 压测和评估工具
└── dataagent-server-demo/  # Demo 应用 - Streamlit 演示界面
```

## 快速链接

- [DataAgent Core README](../libs/dataagent-core/README.md)
- [DataAgent Server README](../libs/dataagent-server/README.md)
- [DataAgent CLI README](../libs/dataagent-cli/README.md)
