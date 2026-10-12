# FACET 算法框架

四通道混合电生理信号 → CSV 校验 → 窗口质量检查 → 滤波 → 32 维特征 → 标准化 → 平衡逻辑回归 → session 留出评估 → JSON 模型 → 回放推理。

这是眼周动作分类基线，不代表情绪识别、独立 EMG 提取或已验证的生理模型。EmoEMG 包名保持兼容，项目展示名为 FACET。

## 安装与完整演示

按根 README 创建 Python 3.11/3.12 虚拟环境并 pip install -e .。以下命令使用该环境的 python；Windows 可直接用 .venv\Scripts\python.exe，无需修改执行策略。

```sh
python -m emoemg simulate --config configs/baseline.json --output data/synthetic
python -m emoemg train --config configs/baseline.json --train data/synthetic/session-0.csv data/synthetic/session-1.csv data/synthetic/session-2.csv --test data/synthetic/session-3.csv --output outputs/synthetic-run-001
python -m emoemg replay --model outputs/synthetic-run-001/model.json --input data/synthetic/session-3.csv --output outputs/synthetic-run-001/predictions.csv
python -m unittest discover -s tests -v
```

输出目录/文件必须不存在，避免覆盖实验。模拟数据只有便于检查流程的人工频率模式，准确率不能用于 Portfolio 的真实效果描述。

## 数据协议

每文件一个连续 session，UTF-8 CSV 列为 timestamp,ch1,ch2,ch3,ch4,label。timestamp 单位秒，严格递增，间隔与配置采样率匹配（5% 容差）。四通道单位、顺序、电极布局和增益必须保持一致。训练每个样本需动作标签；推理可省略 label。中断、丢包或重新连接必须另起文件，不拼接成连续数据。当前不隐式补点或重采样。

采集适配器未来输出此协议。设备型号、实际采样率、单位、参考电极、厂商预滤波及 SDK 尚待确认；配置中的 250 Hz 是演示值。

## 信号与模型

每窗减均值、可选 notch、四阶带通；使用窗口内因果滤波，每窗重置滤波器。训练与回放完全一致，非连续有状态流滤波。窗口结束才预测，默认至少需 1 秒数据，步长 250 ms，未测设备端延迟。

每通道 RMS、平均绝对值、平均波形长度、过零比例，以及四个频带功率，共 32 维。1–45 Hz 是混合头环信号探索基线，不是通用 EMG 频带；真实硬件可能需要不同滤波。更改滤波必须重新训练。

拒绝非有限数、时间不规则和完全平坦通道；尚未实现设备特定饱和阈值、接触质量检测或运动伪迹识别。跨标签窗口在训练中丢弃。推理质量失败输出 unknown；分类 score 未经校准，不能解释成可靠置信度或直接触发鼠标/设备动作。

标准化仅拟合训练数据。显式提供不同 session 作为测试，禁止相同路径或完全相同文件跨集合。用户仍须保证不同文件不是同一 session 的重叠片段，并按受试者分组以评估泛化。不要用测试集调参。报告包括各类 precision/recall/F1、混淆矩阵、窗口数和剔除数。

模型保存为版本化 JSON，包含通道顺序、参数、缩放及分类器权重；推理不加载 pickle。未来扩展模型类型需要新增模型版本和相应推理实现。

## 实施里程碑

1. 已实现：离线协议、基线、模拟 smoke test、回放。
2. 待接入：Windows SDK 采集、事件标记、真实参数与信号质量阈值。
3. 待验证：跨 session/跨日/跨人的真实数据评估。
4. 后续可选：小型 CNN/GRU 与基线对比；足够数据前不默认加深模型。
5. 实时部署：在回放验证后增加环形缓冲和连续设备适配器，实测延迟、拒识和失效行为。

数据、模型和实验输出沿用根 .gitignore，不默认上传。当前远程仓库仍需设置 private；本次代码只落地本机。

本次基线测试使用 Python 3.12，依赖版本见 requirements-baseline-tested.txt。该文件固定算法测试依赖；完整项目依赖仍由 pyproject.toml 管理。Mac/Windows 可用虚拟环境安装，Windows 实机尚未验证。
