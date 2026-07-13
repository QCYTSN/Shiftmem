# ShiftMem 项目骨架设计

## 目标

依据仓库根目录的 `ShiftMem_Implementation_Spec.md` 第 11 节，创建完整、可追踪的项目文件骨架，为后续分阶段实施提供稳定边界。

本次只创建目录、占位模块和基础仓库文件，不实现库存环境、Agent、ShiftMem、Demo、模型调用或实验逻辑。

## 创建范围

- 创建规格中列出的 `configs/`、`src/shiftmem/`、`scripts/`、`demo/`、`tests/`、`artifacts/`、`paper/` 和 `docs/` 结构。
- 创建规格中明确列出的模块文件。
- 为 Python 包目录补充必要的 `__init__.py`。
- Python 占位模块仅包含简短模块说明，不包含可执行的业务实现。
- 创建基础 `README.md`，说明项目目标、当前状态、规格入口和凭证规则。
- 创建 `.env.example`，仅包含空值的 `MODEL_API_KEY`、`MODEL_BASE_URL` 和 `MODEL_NAME`。
- 更新 `.gitignore`，保留 Python 模板规则并加入项目特有的环境、缓存、模型、原始实验结果、大型数据和论文构建产物规则。
- 使用 `.gitkeep` 保留需要存在但允许为空的目录，如配置分类、测试分类和可提交的 artifact 分类。

## 明确保留并提交的内容

以下路径不能被项目规则整体忽略：

- `configs/`
- `tests/`
- `scripts/`
- `data/sample/`
- `artifacts/aggregated/`
- `artifacts/figures/`
- `.env.example`

`artifacts/raw_runs/`、`outputs/`、`runs/`、`logs/`、`data/raw/` 和 `data/processed/` 中的大型或原始内容默认忽略。

## 安全边界

- 不写入任何真实 API Key。
- 不创建真实 `.env`。
- 不接入任何 LLM provider。
- 不修改研究问题、指标或实验公平性规则。
- 暂不添加 `LICENSE`。
- 本次不创建 Git commit。

## 验收标准

1. 文件结构与实施规格第 11 节一致，并包含 Python 包所需的 `__init__.py`。
2. `.gitignore` 覆盖用户指定的项目规则，同时不误伤需要提交的配置、测试、脚本、示例数据和汇总产物。
3. `.env.example` 不含密钥或其他敏感值。
4. 所有 Python 占位模块均可被语法编译，但不包含业务行为。
5. `git status` 仅显示预期的新建或修改文件。
