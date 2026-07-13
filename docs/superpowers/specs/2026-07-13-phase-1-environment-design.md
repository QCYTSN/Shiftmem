# ShiftMem Phase 1 环境与传统基线设计

## 目标与范围

Phase 1 建立可复现的 lost-sales 单品库存模拟环境、合成需求与供应情景、传统非 LLM 基线、无 LLM episode 入口和环境行为验证图。

默认 episode 长度为 150 天，首版仅允许 `supplier_id="standard"`，但动作结构保留供应商字段。Phase 1 不实现 ShiftMem、变化检测器、真实模型 provider、完整实验矩阵或 Demo。

## 技术选择

- Python 3.12 或更高版本
- NumPy：随机数、分布采样和数值计算
- PyYAML：情景配置
- Matplotlib：验证曲线
- pytest：测试
- 自定义轻量环境接口，返回值与 Gymnasium 的 `reset`/`step` 约定一致，但不依赖 Gymnasium

## 组件边界

### 需求模型

`src/shiftmem/envs/demand_models.py` 提供统一需求模型协议，并实现 Poisson 与按均值、离散度参数化的负二项需求。所有随机采样必须使用环境传入的 NumPy RNG，不允许组件自行创建未受控随机源。

需求均值由基础水平、季节因子、促销因子和外生因子的乘积决定。非法均值、离散度或因子应立即报错。

### 供应模型

`src/shiftmem/envs/supply_models.py` 提供单供应商模型。订单根据配置的 lead time 延迟到货，并按 fill rate 决定实际到货量。首版供应商 ID 固定为 `standard`；未知 ID、负订货量、非法 lead time 或 fill rate 应报错。

### Regime shift

`src/shiftmem/envs/shifts.py` 将稳定、突变、渐变、周期、供应、组合和虚警情景表达为确定性的按日参数调度。shift 调度不采样需求，只生成当天的需求与供应参数，因此同一配置与种子可以复现。

首批 YAML 示例覆盖稳定需求、需求均值突变和供应 lead-time 突变。其余 shift 类型通过单元测试验证调度行为。

### 库存环境

`src/shiftmem/envs/inventory_env.py` 提供：

```python
observation, info = env.reset(seed=42)
observation, reward, terminated, truncated, info = env.step(action)
```

一天的事件顺序固定为：处理当日到货、读取当日情景参数、采样需求、以现有库存满足销售、计算 lost sales、接收并排程新订单、计算成本、推进日期。

库存守恒使用：

```text
ending_inventory = starting_inventory + arrivals - sales
```

成本包含采购成本、持有成本、缺货成本和可选固定订货成本，奖励为总成本的负值。采购成本在下单当日按订货量确认；持有与缺货成本在需求实现后确认。

Agent observation 仅包含日期、现有库存、在途总量、最近需求/销售和允许的公开配置，不包含未来 shift、真实分布参数或未来需求。完整成本分解、实际需求、到货和守恒字段写入 `info`，供测试与审计使用。

### 传统基线

`src/shiftmem/agents/classical.py` 实现统一的 `act(observation) -> action` 接口，包含：

- 固定订货策略
- 带种子的随机订货策略
- 移动平均预测与再订货点策略
- 指数平滑预测与安全库存策略
- 使用已知当前分布参数的简化 Oracle 策略

所有策略共享相同动作空间。Oracle 的隐藏信息通过独立方法参数提供，不加入普通 observation。

### 运行与绘图

`scripts/run_episode.py` 读取 YAML，选择传统策略并运行一个 episode，输出总成本、服务水平、总需求、总销售和 lost sales。可选输出结构化运行记录。

`src/shiftmem/evaluation/plots.py` 接收 episode 日志，绘制需求、销售、库存、订货、到货和每日成本曲线，默认保存到 `artifacts/figures/`。

## 配置与数据流

```text
YAML scenario
  -> validated scenario objects
  -> daily regime parameters
  -> demand/supply models
  -> InventoryEnv observation
  -> classical agent action
  -> InventoryEnv transition and cost
  -> episode records
  -> summary metrics and validation figure
```

配置文件是情景参数的唯一入口。相同配置、策略参数和随机种子必须产生完全一致的轨迹。

## 测试策略

使用测试驱动方式实现，覆盖：

1. 同种子轨迹完全一致。
2. 每日库存守恒且 lost-sales 模式库存不为负。
3. 订单只在 lead time 到期后到货。
4. observation 不泄露隐藏状态或未来 shift。
5. 每种 shift 的实际参数轨迹符合配置。
6. 成本分解之和等于总成本，奖励等于总成本负值。
7. 非法动作、配置和模型参数被拒绝。
8. 传统策略输出合法动作。
9. 在固定的简化情景和种子集合中，Oracle 平均成本低于随机策略。
10. CLI 能运行一个 150 天无 LLM episode 并生成验证图。

测试不依赖网络、外部数据集或真实模型。

## 验收标准

- `pytest` 全部通过。
- 一个稳定情景和两个 shift 情景可从 YAML 运行。
- 固定种子可复现完整轨迹。
- episode 输出核心汇总指标并生成一张可读验证图。
- 项目中不存在真实 API 调用或密钥。
- 所有实现决策与规格偏差写入 `docs/implementation_log.md`。
