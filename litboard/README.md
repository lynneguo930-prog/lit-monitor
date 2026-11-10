# 文献看板（LitBoard）

基于 **Next.js App Router + Tailwind CSS v4 + TypeScript** 的移动优先学术主题文献看板。
数据**直接来自浏览器调用 OpenAlex API**，无数据库、无自建后端、无 API Key，可直接部署到 Vercel。

默认主题：**植物结构变异附近的抗病基因（以番茄为主）**，检索式 `tomato structural variation disease resistance gene`。

---

## 功能

| 功能 | 说明 |
| --- | --- |
| 顶部状态 | 显示当前监控主题与检索式，以及「今日已是最新 / 更新了 N 篇文献」；更新数由 localStorage 中的本地基线对比得出 |
| 最新发表 | 近 1 年，OpenAlex 相关度召回后**按 `publication_date` 降序**排列 |
| 精选推荐 | 近 6 年且被引 > 10，按「被引次数 + 时效 + 主题匹配度 + 番茄加权」综合排序，无新文献时主页依然有内容 |
| 文献卡片 | 标题、作者、年份/期刊、一句话摘要预览、被引次数标签、可点击的 DOI 原文外链 |
| 状态视图 | 骨架屏加载、错误态（含 429 专门提示与重试）、空态（可跳转修改检索词） |
| 本地设置 | 检索词与主题名存 localStorage，右下设置面板可随时修改并恢复默认；当前标签页也会记忆 |
| iOS PWA | `manifest.json` + `apple-mobile-web-app-*` meta + `apple-touch-icon` + `viewport-fit=cover` + 安全区 padding，添加到主屏幕后全屏运行 |

### 为什么不是服务端 `sort=publication_date:desc`？

实测 OpenAlex 的 `search` 是宽召回：直接按日期降序时，前排会混入「maize autophagy」「plant volatile compounds」等与主题无关的论文；
按 `cited_by_count:desc` 更会顶上「Nanoparticle classification」这类高被引但完全不相关的文章。
因此两个标签都先用 OpenAlex **默认相关度**召回，再在客户端做关键词命中过滤（`lib/openalex.ts` 的 `topicTokens` / `countHits`），最后分别按日期或综合分排序。

### 更新状态怎么算？

每次成功拉取后，把当前视图的文献 ID 集合与 `localStorage` 中的基线（`litboard:baseline:v1:<query>::<view>`）对比：

- 首次访问：建立基线，显示「今日已是最新」
- 之后有未见过的新 ID：显示「更新了 N 篇文献」
- 无新 ID：显示「今日已是最新」

同时展示「近 7 天 N 篇」与最近同步时间。全部状态都在浏览器本地，不依赖后端。

---

## 目录结构

```
litboard/
├── app/
│   ├── layout.tsx            # metadata / viewport：manifest、PWA、iOS meta、安全区
│   ├── page.tsx              # 主页面（客户端）：状态编排、拉取、基线计算
│   ├── globals.css           # Tailwind v4 入口 + 骨架屏 / 安全区样式
│   └── icon.png              # 自动生成的 favicon
├── components/
│   ├── Header.tsx            # 主题 + 更新状态 + 刷新/设置按钮
│   ├── TabBar.tsx            # 最新发表 / 精选推荐
│   ├── PaperCard.tsx         # 单篇文献卡片
│   ├── SkeletonCard.tsx      # 骨架屏
│   ├── StateViews.tsx        # 错误态 / 空态
│   └── SettingsPanel.tsx     # 检索词底部弹层
├── lib/
│   ├── types.ts              # 共享类型
│   ├── openalex.ts           # API URL 构造、字段解析、倒排摘要还原、排序、错误映射
│   └── storage.ts            # localStorage 读写（SSR 安全、隐私模式降级）
├── public/
│   ├── manifest.json         # Web App Manifest
│   ├── apple-touch-icon.png  # 180×180，iOS 主屏幕图标
│   ├── icon-192.png          # PWA 图标
│   └── icon-512.png          # PWA / maskable 图标
├── scripts/generate_icons.py # 纯标准库图标生成器（可重新生成）
├── .env.example
├── next.config.ts
├── postcss.config.mjs
├── tsconfig.json
└── package.json
```

---

## 本地运行

```bash
cd litboard
npm install
npm run dev
# http://localhost:3000
```

可选环境变量（复制 `.env.example` 为 `.env.local`）：

| 变量 | 作用 |
| --- | --- |
| `NEXT_PUBLIC_OPENALEX_MAILTO` | OpenAlex 礼貌池邮箱，显著降低 429 概率；公开仓库里填公开联系邮箱即可 |
| `NEXT_PUBLIC_DEFAULT_TOPIC_LABEL` | 首次打开时的主题名 |
| `NEXT_PUBLIC_DEFAULT_TOPIC_QUERY` | 首次打开时的英文检索式 |

> 这些是 `NEXT_PUBLIC_*`，会内联到前端代码，**不要放任何密钥**。

---

## 部署到 Vercel

1. 把 `litboard/` 作为仓库根目录推到 GitHub（若放在子目录，在 Vercel 项目 **Settings → General → Root Directory** 填 `litboard`）。
2. Vercel 导入仓库，Framework 自动识别为 **Next.js**，Build Command 用默认 `npm run build`，无需改任何配置。
3. 需要的话在 Vercel **Settings → Environment Variables** 加 `NEXT_PUBLIC_OPENALEX_MAILTO`。
4. 部署完成后用 iPhone Safari 打开：分享 → **添加到主屏幕** → 从主屏图标启动即为全屏 standalone 模式。

因为没有任何服务端代码，也可以 `npx next build` + 静态托管；不依赖 Vercel 特有能力。

---

## 备注与限制

- OpenAlex 匿名调用有限流（实测高峰会出现 429）。页面已做专门错误态与重试；访问量大时建议：
  1. 配置 `NEXT_PUBLIC_OPENALEX_MAILTO` 进入 polite pool；或
  2. 以后增加一层 `app/api/works/route.ts` 薄代理 + `revalidate` 缓存（当前刻意保持零后端）。
- 摘要来自 `abstract_inverted_index`，需按词位置还原；部分预印本没有摘要，卡片会自动隐藏摘要块。
- 没有 Service Worker，因此**不支持离线阅读**；只做主屏幕全屏沉浸体验。如需离线再加 SW 即可。
- 更新基线是「每个设备各自维护」的，与旁边 Python 邮件监控脚本的 `seen_ids.json` 相互独立。
