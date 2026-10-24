# shared

只放与具体页面无关、可被任意 feature 复用的基础设施。

```text
shared/
├── http.ts       统一请求、Bearer 注入、401 续期、ApiError
├── session.ts    浏览器端登录态存储
└── langgraph.ts  LangGraph SDK Client、thread 补建/删除
```

规则：

- `shared` 不能 import `features/`、`routes/`、`app/`。
- 只放跨 feature 的传输与存储基础设施，不放 UI，也不放页面状态。
- 只有出现第二个 feature 且确实重复时，才把代码提升到这里。
