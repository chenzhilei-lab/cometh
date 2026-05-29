# Session Log — 2026-05-28

## 当日概要
- CNN 训练结果确认 + 权重下载
- Relay 中继系统诊断（拉取可用，推送失败）
- 本地 4060 Ti 环境配置（PyTorch CUDA 安装完成，C 盘空间不足待解决）
- 服务器文件同步（train_cometh.py + src/ 推送到 GitHub）

---

## CNN 训练状态确认
- 训练: 113 epochs, Best loss=0.0000
- 权重: `/root/sj-tmp/cometh/weights/cnn_detector.pt` (307MB, May 28 00:36)
- 耗时: ~12h (15:32 → 03:50)
- 数据: 30,000 samples (images.npz 6.5GB + spectra.npz 91MB)

## Ctrl+C 中断问题
- 问题: WebShell 中 Ctrl+C = SIGINT 而非复制, 导致进程被误杀
- 修复: `echo 'stty intr ^\\' >> ~/.bashrc && source ~/.bashrc`
- 效果: Ctrl+C 不再中断进程, 复制用 Ctrl+Shift+C 或右键菜单

## Relay 中继系统
- 问题: `server_poll.sh` 能 `git pull` 但不能 `git push`(无 GitHub 凭证)
- 结果: 单向通信 — 可以下发命令, 无法回传结果
- 替代: 通过 WebShell 直接操作 + 文件管理器传输

## 权重文件下载
- transfer.sh → 被墙
- 最终方案: 算家云文件管理器直接下载 cnn_detector.pt (307MB)

## 文件同步 (GitHub → 服务器)
- 推送文件:
  - `server/train_cometh.py` (18KB) — 完整 PINN+CNN+OOD 训练
  - `server/src/` — 7 个模块 (cnn_detection, pinn_inversion, ood_detector, domain_adapt, hard_constraints, obs_optimizer, \_\_init\_\_)
- 服务器拉取: `cd /root/sj-tmp/cometh-relay && git pull origin main`
- 文件管理器上传失败 (14字节), GitHub 方式可靠

## 本地 4060 Ti 环境
- GPU: NVIDIA GeForce RTX 4060 Ti, 8GB VRAM
- Python: 3.9 (D:\python\python39\) + 3.14 (C:\Users\37639\)
- PyTorch: 2.6.0+cu124 已安装到 Python 3.9
- CUDA DLL: 系统能找到 nvidia-smi, 但 Python 找不到 CUDA 库
- 根因: C 盘只剩 400MB → 虚拟内存不足 → PyTorch 加载 DLL 失败
- 待解决: 清理 C 盘空间 (pagefile.sys / hiberfil.sys / Documents 迁移)

## 3090 服务器状态
- 平台: 算家云 KAl3Y5FV (华南A区)
- WebShell: `root@2b9b8276540d:/workspace`
- GPU: 空闲 (0MB VRAM, 0% utilization)
- 数据: /root/sj-tmp/cometh/data/synthetic/seed_42/
  - images.npz: 6.5GB
  - spectra.npz: 91MB
  - parameters.yaml: 4KB
- 待上传: generate_synthetic_data.py (DIRTY集成版) 已推 GitHub

## 训练计划
### 分工策略
| | 3090 (云端) | 4060 Ti (本地) |
|---|---|---|
| 显存 | 24GB | 8GB |
| 跑什么 | PINN 训练 (18-22GB) | DIRTY数据生成、Afρ计算、OOD拟合 |
| 预算 | ~100 CNY (~40h) | 免费 |

### 待做
1. 腾 C 盘空间 → 4060 Ti 验证 CUDA
2. 本地跑 DIRTY 数据生成
3. 3090 跑缩减版 PINN (5000 samples, 适配预算)
4. Afρ 对比 → 论文 V39

## 注意事项
- 两个终端项目不要混: 算家云=COMETH, AutoDL=医学物理
- Python 3.14 (系统默认) 无 CUDA PyTorch; 用 `D:\python\python39\python.exe`

---

# Session Log — 2026-05-29

## 当日概要
- bypy 上传尝试（MD5 失败）
- 服务器新增权重文件
- 4060 Ti 继续排查 CUDA 问题
- 虚拟内存方案待重启生效

## bypy 百度网盘上传
- bypy 已授权, 配额 105GB (已用 4.1GB)
- 上传 cnn_detector_ep100_final.pt 时 Slice MD5 mismatch, 重试5次均失败
- 建议: 改用文件管理器直接下载, 跳过 bypy

## 服务器权重文件
- `/root/sj-tmp/cometh/weights/`
  - cnn_detector.pt (307MB, May 28 00:36)
  - cnn_detector_ep100_final.pt (307MB, May 28 15:40) — 第二轮训练产物, 耗时约15h
- 两个文件均需下载到本地

## 本地 4060 Ti 环境状态
- C 盘清理后: 400MB → 2.7GB（仍然不够）
- CUDA: False（页面文件太小）
- 解决方案: 虚拟内存移到 D 盘
  - `wmic pagefileset create name="D:\pagefile.sys"` → 创建成功
  - `wmic pagefileset set InitialSize=4096,MaximumSize=8192` → 更新成功
  - C 盘本无 pagefile.sys, 无需删除
  - **已重启, 待验证**

## 下一步
1. 重启本地电脑 → 验证 CUDA: `D:\python\python39\python.exe -c "import torch; print('CUDA:', torch.cuda.is_available())"`
2. 下载服务器权重文件 (cnn_detector.pt + cnn_detector_ep100_final.pt, 各307MB)
3. 4060 Ti 跑 DIRTY 数据生成
4. 3090 跑缩减版 PINN
