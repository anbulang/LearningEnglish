# 自然拼读 · 真机 + 真 DashScope 验收 Runbook（HN-021）

把拼读的**发音生成（TTS）**与**跟读评分（ASR）**接到真 DashScope，并在真机上验收，
覆盖 L1 CVC 与 **L2 digraph / 长元音**（sh、ch、th、wh、a-e、ee、ai/ay）。

## 结论先行（已验证）
`scripts/harness/run_phonics_dashscope_smoke.py`（`make harness-phonics-dashscope-smoke`）
已用**真 DashScope** 跑通完整链路，**无需真机**：
真 TTS 合成 `ship/chip/cake/play` → 经 cloudflared 公网 URL → 真 ASR 转写
→ `score_word_match` 判分。四词全部 `accuracy 1.0 / passed`，转写分别为
`Ship. / Chip. / Cake. / Play.`。证据：`dist/harness/HN-021/phonics-dashscope-smoke-summary.json`。

评分侧不需要为多字母音素做特殊处理：`score_word_match` 是**整词**比对（转写 vs 目标单词），
digraph/长元音天然适用（见 `tests/test_phonics_mvp.py::test_l2_word_scoring_is_whole_word_so_digraphs_pass`）。

## 关键机制 / 硬约束
- **ASR 必须拿到公网可达 URL**。`speaking_assessment._is_public_audio_url` 拒绝
  `localhost/127.0.0.1/192.168.*/10.*/testserver` 等私网/环回地址（`services/api/app/services/shared/speaking_assessment.py`）。
- worker（`phonics.score_attempt`）用 `SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL + object_key`
  拼出交给 DashScope 的录音 URL（`build_speech_assessment_audio_url`）。**这就是公网 URL 的注入点**。
- 手机访问 App 后端用**局域网 IP**即可（`IOS_API_BASE_URL=http://<lan-ip>:8000/v1`）；
  只有「DashScope 去取孩子的录音」这一步需要公网 URL → 用隧道（cloudflared）或公网部署提供。
- 代理网络下需 `AI_HTTP_TRUST_ENV=true` / `MEDIA_HTTP_TRUST_ENV=true` / `SPEECH_ASSESSMENT_HTTP_TRUST_ENV=true`。
- 改后端代码/内容 JSON 后 **必须重启 uvicorn/worker**（`get_settings`、内容加载有进程内缓存）。

## 前置
- `infra/.env` 内已配好真 `DASHSCOPE_API_KEY`、`AI_PROVIDER=qwen`、`MEDIA_PROVIDER=real`、`SPEECH_PROVIDER=dashscope`。
- `cloudflared` 已安装（`brew install cloudflared`）。
- 一台已配对的 iPhone（Apple team `95RDXKW54K`，bundle `com.anbulang.learningenglish`）。

## A. 仅验证 Provider（最快，无真机）
```bash
make harness-phonics-dashscope-smoke
# 期望 summary.status == "passed"，digraph_passed == true
```

## B. 真机端到端
1) 起基础设施 + 迁移（需要 Docker）：
```bash
cp infra/env/local.example.env infra/.env   # 若尚未配置；随后填入真 DASHSCOPE_API_KEY
make infra-up && make api-install && make api-migrate
```
2) 用**真 TTS** 灌拼读音频（发音生成）：
```bash
set -a; . infra/.env; set +a
make phonics-seed PHONICS_SEED_ARGS=--inline-media   # 逐单元生成 sound-card / 单词 / 高频词 mp3
```
3) 起隧道，拿到公网 base，并注入到 ASR：
```bash
cloudflared tunnel --url http://<lan-ip>:8000    # 记下 https://xxxx.trycloudflare.com
export SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL=https://xxxx.trycloudflare.com
```
4) 起后端 + worker（同一套 env，含上面的公网 base）：
```bash
make api-dev            # 或 uvicorn，注意带 SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL
make worker-install && make worker-dev
```
5) 构建并安装到真机（App 指向局域网后端）：
```bash
make mobile-ios-ipa IOS_API_BASE_URL=http://<lan-ip>:8000/v1
# 用 Xcode / devicectl 安装到设备，并在「设置→通用→VPN 与设备管理」信任开发者证书
```
6) 真机验收清单（逐项打勾）：
- [ ] 首页「自然拼读」→ 进入某单元，**听发音/听例词**能播放（TTS 就绪，非「发音生成中」）。
- [ ] 「拼读」步：点各字母块能听单音；点「合起来读」能听整词。
- [ ] 录一个 **L2 digraph 词**（如 `ship`）→「提交给 AI」→ 数秒后出「读得不错！」+ 转写。
- [ ] 再录一个 **长元音词**（如 `cake`）→ 通过。
- [ ] 故意读错/不出声 → 显示「再试一次」（`no_match`），不报错崩溃。
- [ ] 完成 first_sound + 拼读达标后，单元变「已掌握」并解锁下一课。

## 排错
- ASR 一直 `failed`：多半是录音 URL 非公网 → 确认 `SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL`
  是 `https://...trycloudflare.com` 且 `curl <base>/uploads/<key>` 能下到音频。
- TTS 显示「发音生成中」：`--inline-media` 没跑或 `MEDIA_PROVIDER!=real`；重灌并重启后端。
- 公司/校园代理：把三个 `*_HTTP_TRUST_ENV` 设为 `true`。
