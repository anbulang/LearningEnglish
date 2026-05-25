# LearningEnglish 试用操作手册

适用对象：内部测试同学、产品同学、需要完整体验 MVP 主链的非开发人员。

当前版本说明：本文已按 2026-05-25 仓库现状更新，重点反映 AI 校对页自动轮询、真实媒体 provider readiness 边界，以及 speaking 当前仍以 stub 评分为主的事实。

## 1. 你会体验到什么
这次试用的目标是验证一条完整链路：

1. 家长登录
2. 绑定手机号
3. 创建孩子档案
4. 上传讲义
5. AI 校对
6. 开始复习
7. 查看周报

本次试用是开发环境，不需要真实微信账号或真实短信服务。默认仍使用稳定 stub AI；如果开发同学开启 `AI_PROVIDER=doubao`，上传真实讲义后会进入豆包/火山方舟真实识别流程。

## 2. 准备工作
请先让开发同学帮你准备好以下环境：

- 本地后端服务已启动
- 本地 worker 已启动
- iOS Internal/Profile IPA 已导出，或 iOS 模拟器已可直接运行 App

如果你自己在同一台 Mac 上操作，最短启动步骤如下：

```bash
cd /Users/chaucermini/Code/LearningEnglish
cp infra/env/local.example.env infra/.env
make infra-up
make api-install
make worker-install
make api-migrate
```

如果要体验豆包真实识别，请让开发同学在 `infra/.env` 和 API/worker 启动环境中配置：

```bash
AI_PROVIDER=doubao
ARK_API_KEY=<火山方舟 API Key>
DOUBAO_VISION_MODEL_OR_ENDPOINT=<视觉理解 endpoint 或 model>
DOUBAO_TEXT_MODEL_OR_ENDPOINT=<文本解析 endpoint 或 model>
```

没有这些配置时，请保持 `AI_PROVIDER=stub`，否则讲义处理会进入失败状态。

如果使用 Docker Compose 中的 API 和 worker，`make infra-up` 后服务会监听在 `http://127.0.0.1:8000`。另开一个终端启动模拟器 App：

```bash
cd /Users/chaucermini/Code/LearningEnglish/apps/mobile
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000/v1
```

如果你拿到的是 iOS IPA 文件，请让开发同学协助安装到测试设备。

当前已知限制：
- 当前机器已产出 iOS Internal/Profile IPA：`dist/ios/export/learning_english_mobile.ipa`。
- 这个 IPA 是 development provisioning 分发包，只能安装到已纳入 provisioning profile 的测试设备；如果你的设备未注册，需要开发同学先补设备授权或改用 TestFlight。
- 不要使用 Flutter Debug 包做普通真机试用；Debug 包必须通过 `flutter run` 或 Xcode 启动，否则从桌面打开会闪退。
- 真机首次点击登录时，如果 iOS 弹出“允许访问本地网络”，必须选择“允许”，否则 App 无法连接本机开发 API。
- 当前机器尚未产出 Android debug APK，因为未配置 Android SDK / `ANDROID_HOME`。
- 当前真机 `Chaucer` 已验证可以安装并启动该 IPA。其他 iPhone 仍需先确认设备是否已纳入 development provisioning profile。

## 3. 登录方式
当前是开发环境，登录规则固定：

- 点击“微信登录”
- 手机号可以直接使用：`13800138000`
- 验证码固定使用：`123456`

页面上如果出现“开发环境验证码”，也会直接显示相同的验证码。

## 4. 标准试用流程
按下面顺序走，不要跳步骤。

### 步骤 1：登录
- 打开 App
- 等待“正在恢复家长会话...”结束
- 进入登录页后点击“微信登录”

检查点：
- 预期会跳转到“绑定手机号”页面

### 步骤 2：绑定手机号
- 手机号填：`13800138000`
- 点击“获取验证码”
- 验证码填：`123456`
- 点击“完成绑定”

检查点：
- 预期会跳转到首页

### 步骤 3：创建默认孩子档案
如果首页显示“还没有孩子档案”：

- 点击“创建默认孩子档案”

检查点：
- 首页不再是空态
- 之后可以进入资料库、上传页、复习页

### 步骤 4：上传讲义
- 进入“资料库”或首页
- 点击“上传讲义”
- 至少选择 1 张图片
- 点击“完成上传”

检查点：
- 页面跳到“AI 校对”
- 如果是处理中，会看到“AI 理解中”或处理中状态

### 步骤 5：校对讲义
- 等待识别结果出现
- 确认标题、主题、词汇、句型
- 点击确认生成课程详情

检查点：
- 页面跳到课程详情
- 课程状态应为“可复习”或类似状态
- 如果启用了豆包模式，词汇和句型应该来自你上传的真实讲义，而不是固定的 demo 内容。

### 步骤 6：开始复习
- 在课程详情中点击进入复习
- 完成一轮复习任务

检查点：
- 结束后出现“本次复习完成”
- 可以继续进入口语陪练或亲子陪练

### 步骤 7：查看报告
- 进入“报告”页

检查点：
- 本周完成次数增加
- 复习单词数增加
- 如果做了口语陪练，口语尝试次数增加；当前分数与反馈默认来自 stub 评分，不代表真实语音评测结果

## 5. 常见问题
### 一打开就是首页，不是登录页
通常是模拟器里保留了上一次登录状态。

处理办法：
- 如果要重新测试首次登录，请让开发同学先清理模拟器 App 数据
- 如果只是体验主流程，可以直接从首页开始上传讲义

### 上传时报 `Invalid access token`
通常是后端数据库被重置，但模拟器里还保存着旧 token。

处理办法：
- 进入“我的”页面退出登录后重新登录
- 如果退出入口不可用，让开发同学卸载并重新安装模拟器 App

### 登录后一直回到登录页
通常是后端没有启动，或本地 token 已失效。

处理办法：
- 确认 API 服务已经启动
- 重新打开 App 再试一次

### 获取验证码失败
通常是后端服务未启动或接口不可用。

处理办法：
- 确认 API 服务正常
- 重新点击“获取验证码”

### 上传后一直处理中
通常是 worker 没有启动，或者 Doubao 所在网络环境需要系统代理但 API/worker 没有启用 `AI_HTTP_TRUST_ENV=true`。

处理办法：
- 确认 worker 已启动
- 先等待几秒，AI 校对页会自动轮询最新状态
- 如当前网络依赖代理，让开发同学确认 API 和 worker 进程环境里已显式配置 `AI_HTTP_TRUST_ENV=true`
- 如仍未更新，再在 AI 校对页点击“刷新结果”

### AI 校对显示处理失败
如果开启了豆包模式，通常是火山方舟配置不完整、API Key 无效、endpoint/model 名称错误或网络超时。

处理办法：
- 确认 `AI_PROVIDER=doubao`
- 确认 `ARK_API_KEY`、`DOUBAO_VISION_MODEL_OR_ENDPOINT`、`DOUBAO_TEXT_MODEL_OR_ENDPOINT` 均已配置
- 点击重试；如果仍失败，把页面上的失败文案发给开发同学

### 上传失败
通常是图片未正确选择、后端未启动或对象存储不可用。

处理办法：
- 重新选择图片
- 确认 `make infra-up` 已成功
- 确认 API 服务可访问

### 报告页没有变化
通常是复习还没真正提交完成，或者还没做完最后一步。

处理办法：
- 确保完整完成一轮复习
- 返回首页或报告页重新查看

## 6. 试用结束后要反馈什么
请记录以下内容发给开发同学：

- 卡在哪一步
- 页面上看到的报错文案
- 是否能完成“登录 -> 绑定 -> 上传 -> 校对 -> 复习 -> 报告”
- 哪个页面最难理解
- 哪个按钮/入口最不明显

如果可以，请附上截图。

## 7. 当前交付状态
截至 2026-05-01，自动化主链和 iOS IPA 导出已通过：

- API：登录、绑定、创建孩子、上传、进入 AI 校对
- 移动端：上传成功后跳转 AI 校对页，AI 校对确认后跳转课程详情
- Harness：`HARNESS_RESET=1 make harness-mvp-readiness` 可以完成到测试和模拟器构建阶段
- iOS：`make mobile-ios-ipa` 已成功导出 `dist/ios/export/learning_english_mobile.ipa`
- 真机：`Chaucer` 已验证可以安装并启动 `com.anbulang.learningenglish`

尚未完全满足“任意非开发设备直接安装”的条件：

- iOS IPA 只能安装到已纳入 development provisioning 的设备；更多设备需要注册 UDID 或走 TestFlight
- Android APK 需要先安装 Android SDK
