# 🤝 贡献指南 · Contributing

感谢你愿意为 WSLens 出力！这份文档说明如何参与，以及我们对提交的期望。

## 🧭 参与方式

| 方式 | 说明 |
| --- | --- |
| 🐛 报告 Bug | 提交 Issue，附上命令、输出、`python --version` 与操作系统 |
| 💡 功能建议 | 提交 Issue，写清「场景 → 现状痛点 → 期望行为」 |
| 📝 文档改进 | 直接 PR，三个语言版本的 README 欢迎一起更新 |
| 🔧 代码贡献 | Fork → 分支 → 提交 → PR |

## 🛠️ 本地开发

```bash
git clone https://github.com/gitstq/WSLens.git
cd WSLens

python -m wslens selftest    # ① 基线自测（7/7）
python tests/run.py          # ② 单元测试（44 项）
bash scripts/build.sh        # ③ 构建 + 冒烟验证
```

不需要创建虚拟环境，也不需要 `pip install -r requirements.txt`（本项目运行时依赖为零）。

## 🚧 三条硬性约束

1. **零第三方运行时依赖** —— 只用 Python 标准库。这是项目的核心承诺，也是它能进内网、能离线运行的前提。
2. **新增能力必须带测试** —— 协议层改动要有编解码用例，CLI 改动要有行为用例。
3. **三语文档同步** —— 涉及用户可见行为的改动，需同步 `README.zh-CN.md`、`README.zh-TW.md`、`README.en.md`。

## 📜 提交信息规范（Angular）

```
feat: 新增 xxx 功能
fix: 修复 xxx 问题
docs: 更新 xxx 文档
refactor: 重构 xxx 模块
test: 补充 xxx 用例
chore: 调整构建脚本
perf: 优化 xxx 性能
```

## ✅ PR 检查清单

- [ ] `python tests/run.py` —— 44 项全绿
- [ ] `python -m wslens selftest` —— 7/7 通过
- [ ] 未引入任何第三方运行时依赖
- [ ] 新增能力已补充单元测试
- [ ] 三语 README 已同步（如涉及用户可见变更）
- [ ] 提交信息符合 Angular 规范

## 🧪 测试约定

- 测试文件放在 `tests/`，命名 `test_*.py`
- 使用标准库 `unittest`，**不引入 pytest 作为必需依赖**
- 需要真实连接的测试，请使用 `wslens.echod.start_background_server` 起本地服务，保证离线可跑
