# FACET / EmoEMG 跨电脑协作记录

更新日期：2026-10-12。

## 已确认的研究范围

使用实验室现有四通道 EEG 头环，研究通常被作为干扰丢弃的眼周非脑电相关信号。
第一阶段检测眨眼、皱眉、挑眉等可标注动作，并训练小模型；暂不使用 FPV/VLM，不做情绪识别。
动作标签不等于 EMG/EOG 生理源标签，动作分类成功不等于已实现源分离。
长期研究这些成分是否能帮助更有针对性地去除干扰，同时避免损失真正脑电。

先保留清洗前原始信号，用同步眼周视频标记实际动作起止；有条件时用参考 EOG/EMG 验证来源。
静息、用力闭眼、咬牙、转头可用于检查误报。评估按完整 session、重戴时段或被试划分，避免相邻窗口泄漏。
关注各动作 precision/recall、混淆矩阵和连续静息时每分钟误报数。

## 用户指定的工作分工

- Mac / 云端用于开发、研究讨论和代码管理。
- 所有后续测试在 Windows 本地执行，包括环境检查、单元测试、模拟训练/回放与真实头环测试。
- 通过 https://github.com/yutongwuu/facet-artifacts 同步代码和本文件。
- GitHub 不会自动同步这段聊天历史；Windows 中的 Codex 应读取本文件和 FRAMEWORK.md 接续工作。
- 原始被试数据、视频、训练模型和实验输出默认被 Git 忽略，不随代码上传。

## Windows 首次接续（PowerShell）

先安装 Git 和 Python 3.11 或 3.12。以下以 Python 3.11 为例：

```powershell
git clone https://github.com/yutongwuu/facet-artifacts.git
cd facet-artifacts
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe scripts/check_environment.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

之后在 Windows Codex 中打开这个仓库文件夹，要求先读取本文件与 docs/FRAMEWORK.md。
已克隆的仓库，在工作区干净时运行 `git pull --ff-only` 获取更新。
Windows 修改代码或记录后，提交并 push；Mac 也需要 pull 才能获得这些更新。
遇到本地未提交变更时先保留并提交，不用 reset 覆盖。

## 当前状态与待办

- Mac 本地已有离线算法框架、配置与测试文件；它们的存在不表示 Windows 测试已通过。
- 既有 FRAMEWORK.md 记载过 Mac 上的基线验证；用户现已指定后续测试全部在 Windows。
- 用户截图显示云环境 facet-artifacts 已创建，状态 Unpublished；尚未确认发布成功。
- 云环境是否发布不影响 Windows clone 仓库和本地测试。
- 头环型号、电极位置、参考电极、采样率、原始单位、内部滤波和 Windows SDK 尚待确认。
- configs/baseline.json 中的采样率是演示参数，接入硬件前必须核实。
- 此记录是研究讨论摘要，不是完整聊天导出。
