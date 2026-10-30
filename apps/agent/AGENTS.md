# agent

## 目录

```text
apps/agent/
├── agent/
│   ├── main.py                  # build_exp_agent / build_teach_agent
│   ├── core/
│   ├── infra/
│   ├── runtime/
│   ├── resources/
│   │   ├── prompt/
│   │   │   ├── base.md
│   │   │   ├── lab.md
│   │   │   └── teaching.md
│   │   └── skills/
│   │       ├── common/
│   │       │   ├── diagrams/
│   │       │   └── memory-maintenance/
│   │       ├── lab/
│   │       │   └── traceroute-lab/
│   │       └── teaching/
│   │           ├── ask-question/
│   │           │   └── bank.md
│   │           └── computer-networks-textbook/
│   │               └── textbook/
│   └── tools/
│       ├── ask_student.py
│       ├── question_bank.py
│       └── schemas/
├── tests/
├── langgraph.json
├── pyproject.toml
└── uv.lock
```