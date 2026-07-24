<div align="center">

# ShiftMem

### 面向环境变化的库存智能体条件记忆系统

一个证据优先的研究系统，用于分析：当需求或供应环境发生变化后，
LLM 智能体应当继续使用、修正，还是停用过去的运营经验。

[English](README.md) · [简体中文](README.zh-CN.md)

[![CI](https://github.com/QCYTSN/Shiftmem/actions/workflows/ci.yml/badge.svg)](https://github.com/QCYTSN/Shiftmem/actions/workflows/ci.yml)
[![在线网页端](https://github.com/QCYTSN/Shiftmem/actions/workflows/deploy-pages.yml/badge.svg)](https://qcytsn.github.io/Shiftmem/)
[![论文](https://img.shields.io/badge/Manuscript-LaTeX%20source-3D6117?logo=latex&logoColor=white)](paper/README.md)
[![PDF](https://img.shields.io/badge/Paper-PDF-B31B1B?logo=adobeacrobatreader&logoColor=white)](paper/ShiftMem.pdf)
![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/Demo-React%20%2B%20TypeScript-149ECA?logo=react&logoColor=white)
![冻结证据](https://img.shields.io/badge/Evidence-SHA--256%20frozen-147D72)
[![License: MIT](https://img.shields.io/badge/Code%20License-MIT-F2C94C.svg)](LICENSE)

</div>

---

> ## 🔬 ShiftMem Evidence Lab · 在线网页端
>
> 交互式回放完整的 160-cell 冻结实验，对比 ShiftMem 与 VectorMemory，
> 检查记忆生命周期，并将界面中的结果追溯到经过校验的正式证据。
>
> **[在浏览器中打开 Evidence Lab →](https://qcytsn.github.io/Shiftmem/)**<br>
> 无需安装、无需 API Key，也不会调用模型服务。
>
> [本地启动](#运行-demo) · [Demo 使用说明](demo-web/README.md) ·
> [产品与证据完整性规范](docs/demo_design_spec.md) ·
> [正式实验审计](docs/v2_formal_post_test_audit.md)

> ## 📄 论文 · 完整源文件
>
> **Does Conditional Memory Help an LLM Inventory Agent under Regime Shifts?**<br>
> **A Systems Evaluation Frozen before Test-Outcome Access**
>
> 仓库现已包含完整 LaTeX 论文、参考文献、投稿级图、源数据表，以及可复现的
> 论文图生成脚本。
>
> **[打开论文说明 →](paper/README.md)** ·
> **[下载编译版 PDF](paper/ShiftMem.pdf)** ·
> [主 TeX 文件](paper/main.tex) ·
> [论文图](paper/figures/) ·
> [论文表](paper/tables/)

## 项目概览

| | |
| --- | --- |
| **研究问题** | 面对需求和供应变化，条件记忆能否改善 LLM 引导的库存适应？ |
| **LLM 权限** | 只能调整三个有界策略参数；每日订货仍由确定性控制器执行 |
| **正式实验** | 160 个完整 cells、2 个模型、2 种方法、8 个留出场景、5 个配对种子 |
| **主要终点** | 70 个配对的变化适应样本 |
| **主要结论** | ShiftMem 整体上没有优于 VectorMemory |
| **证据状态** | 已冻结、已校验、可离线验证与复现 |
| **论文状态** | 已完成 LaTeX 正文、3 幅投稿级图、3 组源数据表、参考文献和附录 |

## 论文

论文完整报告了系统评估，包括主要负结果、考虑依赖结构的敏感性分析、
描述性子组结果、可靠性审计、局限和证据可用性声明。论文主张严格对应
冻结的 Protocol-v2 输出，不从交互式 Demo 中选择性提取结论。

- [论文结构与编译说明](paper/README.md)
- [编译版论文 PDF](paper/ShiftMem.pdf)
- [论文主文件](paper/main.tex)
- [论文图](paper/figures/)与[源数据表](paper/tables/)
- [论文图生成脚本](scripts/make_paper_figures.py)
- [代码与数据可用性声明](paper/availability.tex)

## 为什么需要 ShiftMem？

环境变化后，过去正确的运营经验可能变成误导。ShiftMem 不把记忆视为
永久有效的事实，而是带有适用条件、可以变化的经验：

- 经验会记录其形成时的环境条件；
- 环境变化可以让记忆进入休眠，而不是直接删除；
- 后续证据可以支持、降级或重新激活一条记忆；
- 策略提案必须明确引用实际检索到的记忆；
- 延迟到达的运营结果会更新记忆生命周期。

LLM **不能直接下达每日订单**，只能提出：

1. 需求预测窗口；
2. 安全库存系数；
3. 提前期缓冲。

真正的库存决策由共享的确定性控制器执行。智能体无法看到未来需求、
隐藏的 regime 标签或 Oracle 信息。

```mermaid
flowchart LR
    A["公开库存历史"] --> B["变化检测器"]
    A --> C["策略复核调度器"]
    B --> C
    C --> D["条件记忆检索"]
    A --> E["有界 LLM 策略复核"]
    D --> E
    E --> F["结构与参数边界校验"]
    F --> G["确定性每日控制器"]
    G --> H["库存环境"]
    H --> A
    H --> I["延迟结果验证"]
    I --> D
```

## 运行 Demo

公开的只读网页端已经上线：
**[qcytsn.github.io/Shiftmem](https://qcytsn.github.io/Shiftmem/)**。网页由
GitHub Actions 从冻结证据包自动部署，不会调用模型服务。

如需本地检查或开发，可按下面的步骤启动。本地版与网页端使用同一份经过
校验的证据导出。

环境要求：Python 3.12+、Node.js 22+ 和 pnpm。

```powershell
git clone https://github.com/QCYTSN/Shiftmem.git
cd Shiftmem

py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"

# 校验证据并生成确定性的浏览器数据。
python -m demo.export_web

# 启动 Evidence Lab。
cd demo-web
corepack enable
pnpm install --frozen-lockfile
pnpm dev
```

浏览器打开 **http://127.0.0.1:5173**。

前端不会扫描原始运行目录。对于全新克隆的仓库，Python 会先校验已追踪
的冻结发布包及其中所需的证据文件，再生成浏览器可读取的视图模型。

Evidence Lab 包含四个互相关联的页面：

- **Episode Lab**：同步回放需求、库存、订单、成本、策略复核、fallback
  和环境变化；
- **Compare**：严格配对比较 ShiftMem 与 VectorMemory；
- **Memory Audit**：检查记忆的检索、引用、支持、失败、休眠与重新激活；
- **Evidence & Method**：展示数据来源、术语、汇总结果和明确的主张边界。

## 正式实验结果

预注册的 Protocol-v2 主要分析始终是权威结果。

| 分析 | ShiftMem − VectorMemory | 95% 区间 | p 值 | 解释 |
| --- | ---: | ---: | ---: | --- |
| 预注册主要分析 | +45.44 | [-2.72, 93.60] | 0.203 | 不支持 H1 |
| 聚类均值敏感性分析 | +45.44 | [11.26, 79.09] | 0.041 | 事后分析；对 ShiftMem 不利 |

正值代表 ShiftMem 的 30 天 Oracle-relative cost gap 更高。在 70 个主要
配对中，ShiftMem 胜 25、平 11、负 34。Test-ID 基本中性（-2.67），
Test-OOD 对 ShiftMem 不利（+81.53）；DeepSeek 与 MiniMax 的方法效应
方向也相反。

这是被完整保留的负结果，而不是“项目失败”：当前证据否定了普遍优越性
的强主张，同时显示记忆效果可能取决于模型和具体环境。

## 校验正式证据

验证过程确定、离线，而且不需要凭据：

```powershell
python -m pytest -q
python scripts/verify_release_archive.py
```

预期闭包状态：

- 160/160 个正式 cells；
- 70 个主要配对样本；
- 11/11 个原始证据来源校验通过；
- 0 个未解决 reservation；
- 闭包标识 `v2-formal-results-f4ab41daacf3`。

保留原始目录结构的研究工作区还可以重新生成并比较全部聚合结果：

```powershell
python scripts/finalize_formal_results.py --verify
```

### 主要证据入口

- [证据 manifest](artifacts/aggregated/v2_formal_evidence_manifest.json)
- [正式统计分析](artifacts/aggregated/v2_formal_statistical_analysis.json)
- [可靠性审计](artifacts/aggregated/v2_formal_reliability_audit.json)
- [冻结原始证据包](artifacts/releases/v2-formal-results-f4ab41daacf3-raw-evidence.zip)
- [证据包校验文件](artifacts/releases/v2-formal-results-f4ab41daacf3-raw-evidence.sha256.json)

## 可靠性也是实验结果

Provider 和解析失败均被保留在最终业务结果中：

| 信号 | 观测值 |
| --- | ---: |
| 策略复核 | 5,176 |
| Cell 内记录的调用尝试 | 6,189 |
| 解析失败 | 1,680（27.1%） |
| 保留原策略的 fallback | 667（复核的 12.9%） |
| Provider 终止失败 | 1,705 |
| 未解决 reservation | 0 |

因此，本实验评估的是包含 fallback 行为在内的实际系统表现，并没有把
“纯记忆机制”与模型指令遵循能力、Provider 可靠性完全分离。

## 仓库导航

| 路径 | 内容 |
| --- | --- |
| [`paper/`](paper/README.md) | 完整论文源文件、参考文献、图表与编译说明 |
| [`demo-web/`](demo-web/README.md) | 正式 React + TypeScript Evidence Lab |
| [`demo/`](demo/README.md) | 经过校验的 Python 证据适配与导出层 |
| [`src/shiftmem/`](src/shiftmem/) | 环境、智能体、记忆生命周期、控制器与评估 |
| [`configs/`](configs/) | 实验、数据划分、验证和冻结配置 |
| [`scripts/`](scripts/) | 校验、聚合与显式实验入口 |
| [`tests/`](tests/) | 单元与集成测试 |
| [`artifacts/aggregated/`](artifacts/aggregated/) | 机器可读的正式结果 |
| [`artifacts/releases/`](artifacts/releases/) | 冻结证据发布包及校验信息 |
| [`docs/`](docs/README.md) | 协议、审计、报告、模型卡和项目历史 |

## 适用范围

当前证据来自合成的单品缺货损失库存环境，覆盖两个 Provider 托管的模型
系列、一个三参数有界控制器，以及每个场景五个随机种子。它不能证明对
所有记忆系统的普遍优越性，也不能证明记忆休眠的因果收益，或直接推广到
真实的多品类企业库存系统。

完整解释、局限和允许提出的主张，请参阅
[正式 post-Test 审计](docs/v2_formal_post_test_audit.md)。

## 许可证

本仓库的软件源代码采用 [MIT License](LICENSE)。

`paper/` 目录中的论文、编译版 PDF、图、表、参考文献和其他学术内容不属于
MIT 授权范围；除未来出版方或存档平台另行规定外，其版权归 Fengkai Gao
所有，保留全部权利。详见[论文专用版权声明](paper/LICENSE)。
