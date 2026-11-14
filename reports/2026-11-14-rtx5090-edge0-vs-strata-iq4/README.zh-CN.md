# RTX 5090 — Edge0 NVFP4 与 Strata IQ4 实测归档

[English full report](README.md) · [硬件](../../hardware/rtx5090-9800x3d-128gb.json) · [配置快照](configuration.json)

测试日期为 2026-11-14，硬件为 RTX 5090 32GB、Ryzen 7 9800X3D、128GB 内存，原生 Windows 11。归档包含部署验收、同题速度、13 项参数初筛及扩大质量测试。

| 实测项目 | Edge0-145B-NVFP4 优化后 | Qwen3.8 Flash Next UD-IQ4_XS-v31 |
|---|---:|---:|
| 持续代码生成 | 104.7 tok/s | 151.5 tok/s |
| 首个内容片段延迟中位数 | 0.927 秒 | 1.192 秒 |
| 复杂代码 | 7/12 | 9/12 |
| 中文推理 | 16/16 | 16/16 |
| 多轮模拟工具 | 12/12 | 12/12 |
| 质量总分 | 35/40 | 37/40 |
| 质量测试模型请求时间合计 | 603.1 秒 | 466.9 秒 |

Edge0 代码生成慢 30.9%，质量测试模型请求时间多 29.2%。我的选择是暂不推荐 Edge0，继续观察更新，同级别优先使用 Qwen v31。这个判断基于两套本地部署及本次题集。

## 测试条件与边界

- 两套配置的上下文上限均为 32768。Edge0 1 槽、Strata 8 槽，实际始终单客户端串行请求。
- 速度测试为两题、两轮，每请求生成 1024 tokens，关闭思考，temperature=0、seed=42。主要比较实际输入为 114 或 120 tokens，输入缓存为 0。
- 质量测试为 20 道合成任务各重复两次，ABBA 顺序。开启思考，代码及中文预算 1536 tokens，工具预算 768，每响应上限 6144 tokens。实际输入 134–4068 tokens。
- 两模型各完成 80 个 API 请求及 60 次模拟工具调用。代码及独立中文请求缓存为 0；工具对话各有 40/52 个 API 回合复用前缀，最高 1176 tokens。
- 6 道代码题合计 216 项正常及边界检查；最终重新验算 24 份代码，分数未变。中文和工具均满分，这部分题目区分度有限。
- 两轮是相同 20 题的重复尝试。架构、量化、运行时、槽数及内存配置不同，结果用于比较这两套实际部署。

## 部署与优化

- 官方 edge0-infer 配合 edge0-strata，源码 `f833336e487f61848ab5d49b2e7d06678812ea8a`，权重 revision `cf9b3679e7da201a658a694e1730607193f2b032`。
- 27 文件共 112854101214 字节，全部 LFS SHA-256、普通 Git blob SHA-1 校验通过。原 Strata 四个 GGUF 分片 SHA-256 复核通过。
- Q8 D/U、INT8 KV、PLE direct、MTP 4、阈值 0.5，GPU 预留 3072 MiB，系统内存余量 16 GiB。最终启用 `--adapt-async 1`，提升约 4%–7%。
- 首次就绪 27.197 秒，重启 17.761 秒。中文、代码、多轮和 30476-token 输入验收通过。长输入处理约 2140 tok/s，是引擎请求计时口径。
- 原始服务运行状态均为测试当时记录。归档操作未重新跑模型、启停服务或修改生产配置。

## 文件

- [部署细节](deployment-notes.zh-CN.txt)、[速度及优化细节](speed-notes.zh-CN.txt)、[质量细节](quality-notes.zh-CN.txt)
- [速度逐请求 CSV](data/speed-requests.csv)、[质量逐任务 CSV](data/quality-tasks.csv)、[质量逐请求 CSV](data/quality-requests.csv)
- [速度响应及采样](data/speed-details.json)、[质量响应及模拟工具记录](data/quality-details.json)、[题集](data/quality-suite.json)、[权重清单](data/weight-manifest.json)
- [复现与启动脚本](scripts/README.md)、[英文图文及图片列表](README.md#english-image-list-and-x-draft)、[X 推文草稿](social/X-post.txt)

公开版以占位符替换本机路径、账户及内部接口地址，并排除主机进程清单和服务日志。英文报告包含完整方法、限制和配置初筛表。
