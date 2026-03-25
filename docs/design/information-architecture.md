# LearningEnglish Information Architecture

## Navigation Model
The app uses one shared information architecture across phone and tablet. Layout changes with breakpoint, but destinations and entity names remain fixed.

### Parent mode primary destinations
1. `首页`
2. `资料库`
3. `复习`
4. `报告`
5. `我的`

### Child mode entry points
- Start today's review
- Continue an unfinished practice session
- Enter speaking mode

## Screen Map
```text
首页
├─ 今日待复习
├─ 最近课程
├─ 本周进度
└─ 快速入口
   ├─ 上传讲义
   ├─ 开始复习
   └─ 亲子陪练

资料库
├─ 课程列表
├─ 搜索/筛选
├─ 上传扫描
├─ 识别处理中
├─ 人工校对
└─ 课程详情
   ├─ 原始讲义
   ├─ 词汇
   ├─ 句型
   ├─ 对话
   └─ 本课复习包

复习
├─ 今日任务
├─ 单词卡
├─ 听音选图
├─ 配对/选择
├─ 跟读
├─ AI 口语陪练
└─ 亲子陪练

报告
├─ 周复习包
├─ 本周数据
├─ 薄弱点
└─ 推荐复习内容

我的
├─ 多孩子管理
├─ 档案设置
├─ 家长偏好
└─ 设备与通知
```

## Core Objects
### Child profile
- One child identity and learning context
- Used to scope lessons, review tasks, and reports

### Course material
- One uploaded lesson package containing images, OCR text, and source metadata

### Knowledge pack
- AI-structured result of a course material
- Includes vocabulary, sentence patterns, dialogues, topic, and recommended tasks

### Review task
- A single playable exercise item or guided activity

### Practice session
- A completed or in-progress run through one or more review tasks

### Report
- Aggregated learning progress and weak-point insights

## Device Adaptation Rules
### Phone
- Bottom navigation
- One main task per screen
- Full-screen flows for scan, review, and speaking

### Tablet
- Navigation rail or left-side navigation
- Split view for list and detail
- Persistent context panels for lesson source, extracted content, and progress

## Key Journeys
### Lesson capture journey
`首页 -> 上传讲义 -> 识别处理中 -> 人工校对 -> 课程详情 -> 生成复习包`

### Same-day review journey
`首页今日待复习 -> 课程详情 -> 单词卡 -> 轻量练习 -> 跟读 -> 口语问答`

### Parent coaching journey
`首页/报告 -> 推荐陪练 -> 亲子陪练 -> 记录完成情况`

### Weekly catch-up journey
`报告 -> 周复习包 -> 错误高频项 -> 重新练习`
