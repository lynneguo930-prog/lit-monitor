# lit-monitor · 学术主题文献监控与看板

围绕「**植物结构变异附近的抗病基因（以番茄为主）**」的一套轻量工具：

- **每天自动推送新文献到邮箱** —— Python 脚本检索 OpenAlex 近 7 天文献，去重后用 Resend 发一封 HTML 邮件；GitHub Actions 每天 UTC 08:00 定时运行，并把去重记录回写到仓库。
- **随时可看的移动端文献看板** —— Next.js + Tailwind CSS 纯前端页面，浏览器直连 OpenAlex，提供「最新发表 / 精选推荐」两个视图，支持 PWA / iOS 添加到主屏幕全屏运行。
- **全量中文归档页** —— 同一检索窗口下的全部文献（英文标题 + 中文题名、中文摘要、DOI 外链），带搜索与主题相关度筛选。

无需自建后端、无需数据库：去重状态是一个 `seen_ids.json`，看板是纯静态页面。

---

## 目录结构

```
.
├── .github/workflows/check_papers.yml   # 定时任务：检索 → 发信 → 回写 seen_ids.json
├── openalex_lit_monitor.py              # 核心单文件脚本（检索 / 去重 / 渲染 / 发信）
├── main.py                              # CI 入口，转发到上面的 main()
├── requirements.txt                     # Python 依赖
├── verify_resend.py                     # 零依赖的 Resend 配置自检（Key / 发件人 / 投递）
├── generate_archive.py                  # 重查同窗口文献并渲染全量归档页
├── translate_papers.py                  # 批量机翻标题与摘要，结果缓存到 translations.json
├── seen_ids.json                        # 已推送文献 ID（由 Actions bot 自动提交）
├── LICENSE                              # MIT
└── litboard/                            # Next.js 看板（可独立部署到 Vercel）
    ├── app/                             # layout / page / 全局样式
    ├── components/                      # Header / TabBar / PaperCard / Skeleton / ...
    ├── lib/                             # OpenAlex 数据层、localStorage、类型
    ├── public/                          # manifest.json、PWA 图标、papers-archive.html
    └── README.md                        # 看板专属说明
```

## 快速开始 · 邮件推送

```bash
pip install -r requirements.txt

export RESEND_API_KEY="re_xxx"
export ALERT_TO_EMAILS="you@example.com"
export RESEND_FROM="Literature Bot <bot@your-verified-domain.com>"   # 可选
export OPENALEX_MAILTO="you@example.com"                             # 可选，礼貌池

python openalex_lit_monitor.py
```

无新增文献时脚本直接退出、不发邮件；`seen_ids.json` 采用原子写入，只有邮件发送成功后才落盘，发送失败时下一轮会自动重试。

### 环境变量

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `RESEND_API_KEY` | ✅ | — | Resend API Key |
| `ALERT_TO_EMAILS` | ✅ | — | 收件邮箱，多个用英文逗号分隔 |
| `RESEND_FROM` | — | `onboarding@resend.dev` | 生产环境请改为已验证域名；测试发件人只能投递到 Resend 账号邮箱 |
| `OPENALEX_MAILTO` | — | 取第一个收件邮箱 | OpenAlex 礼貌请求池标识 |
| `SEARCH_QUERIES` | — | 内置 3 条番茄主题检索式 | 多条用英文分号 `;` 分隔 |
| `TOPIC_LABEL` | — | 中文主题名 | 邮件标题与正文展示 |
| `LOOKBACK_DAYS` | — | `7` | 回溯天数 |
| `MAX_PAGES` | — | `10` | 每个检索式最大翻页数 |
| `MAX_EMAIL_ITEMS` | — | `50` | 单封邮件最多展示篇数，超出的只记 ID 不展开 |
| `SEEN_FILE` | — | 脚本同目录 `seen_ids.json` | 去重记录路径 |
| `LOG_LEVEL` | — | `INFO` | 日志级别 |

### GitHub Actions

在 **Settings → Secrets and variables → Actions** 中配置：

- **Secrets**：`RESEND_API_KEY`（必填）、`RECIPIENT_EMAIL`（收件人，覆盖工作流默认值）、`RESEND_FROM`（可选）
- **Variables**（可选）：`OPENALEX_MAILTO`、`SEARCH_QUERIES`、`TOPIC_LABEL`、`LOOKBACK_DAYS`、`MAX_PAGES`、`MAX_EMAIL_ITEMS`、`LOG_LEVEL`

另外请确认 **Settings → Actions → General → Workflow permissions** 为 **Read and write permissions**，否则机器人无法把 `seen_ids.json` 推回仓库。`schedule` 只在默认分支生效。

## 快速开始 · 文献看板

```bash
cd litboard
npm install
npm run dev            # http://localhost:3000
npm run build          # 标准 Next.js 生产构建
STATIC_EXPORT=1 npm run build   # 纯静态导出到 out/，可托管到任意静态服务/CDN
```

Vercel 导入仓库后把 **Root Directory** 填 `litboard`，其余保持默认即可。可选环境变量 `NEXT_PUBLIC_OPENALEX_MAILTO` 用于进入 OpenAlex 礼貌池、降低 429 概率。

看板完全在浏览器侧调用 OpenAlex（已确认 CORS 开放），包含骨架屏、错误/空状态、检索词与标签页 localStorage 缓存、iOS 全屏 meta 与 PWA 图标。

## 全量中文归档页

```bash
python generate_archive.py            # 重新检索并渲染，产出 papers_archive.html
python generate_archive.py --from-cache   # 用已有缓存离线重渲染
python translate_papers.py            # 批量机翻（增量、可断点续跑）
python translate_papers.py --repair   # 补翻失败的长摘要
```

译文为公共翻译接口的机器翻译，仅供快速浏览，卡片内可展开英文摘要原文核对。归档页是**静态快照**，看板才是实时数据。

## 数据来源与许可

- 文献元数据来自 [OpenAlex](https://openalex.org/)（CC0），请遵守其[礼貌请求池](https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication)约定，通过 `mailto` 标识自己。
- 代码采用 **MIT License**（见 `LICENSE`）。文献元数据与机翻译文不属于本仓库代码许可范围。
- 邮件发送依赖 [Resend](https://resend.com/)，看板翻译依赖 [MyMemory](https://mymemory.translated.net/)；两者均为第三方服务，使用时请遵守各自条款。

> 请勿把 API Key 写入源码或提交到仓库，一律使用环境变量 / GitHub Secrets。
