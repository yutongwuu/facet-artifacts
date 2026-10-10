# EmoEMG

利用实验室现有四通道 EEG 头环的混合信号，检测眨眼、皱眉、挑眉等眼周动作。
初期标签表示动作；分类成功不等于生理源分离。暂不做情绪识别。

## 环境

- Windows 本地：头环驱动、厂商软件或 SDK、原始数据采集，以及未来的实时推理。
- Mac / Codex Cloud：离线分析、数据处理与小模型训练。
- GitHub：同步代码与配置。实验数据另行管理，默认不进入 Git。

项目推荐 Python 3.11。以下命令在仓库根目录执行。

### Windows（PowerShell）

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe scripts/check_environment.py
```

直接调用虚拟环境解释器，无需改变 PowerShell 执行策略。
厂商驱动与 SDK 待确认头环型号后安装；当前配置尚不支持连接真实头环。

### Mac / Linux

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python scripts/check_environment.py
```

可选依赖：把安装命令中的 `.` 换成 `'.[notebook]'` 或 `'.[train]'`。
第一阶段默认使用 CPU 和传统分类基线；未假定云环境有 GPU。
目前依赖为版本范围，尚未生成经过安装验证的锁文件。

## 创建 Codex Cloud 环境

本地配置文件不等于已发布的云环境。完成 GitHub 仓库连接后：

1. Settings → Codex Cloud → Environments → Create environment。
2. 选择 EmoEMG GitHub 仓库，环境名称建议 `EmoEMG`，访问设为 Only me。
3. 在环境设置对话中要求 Python 3.11，并运行 `bash scripts/setup_cloud.sh`。
4. 允许安装依赖所需的 Package managers 网络访问。
5. 确认环境检查成功、审阅设置报告，然后 Publish。

初期环境不需要密钥，也不需要接入被试数据。
官方说明：https://learn.chatgpt.com/docs/environments/cloud-environments

## 下一步

确认头环型号、四个电极位置、参考电极、采样率、原始数据接口与 Windows SDK。
然后实现设备接入、动作提示与事件标记。
