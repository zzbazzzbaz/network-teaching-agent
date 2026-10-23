# shared

只放与业务无关、可被任意 feature 复用的东西。

```
shared/
├── ui/    通用展示组件（按钮、空态、弹层）
└── lib/   纯函数、格式化、常量
```

规则：

- `shared` **不能** import `features/`、`routes/`、`app/`。
- 通用组件不得包含聊天、会话、agent 等业务概念。
- 只有出现第二个 feature 且确实重复时，才把代码提升到这里。
