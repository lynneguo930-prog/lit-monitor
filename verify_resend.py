#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resend 配置自检（零第三方依赖，不需要 pip install）。

作用：在把 API Key 填进 GitHub Secrets 之前，先在本机确认
  1) API Key 是否有效
  2) 账号下有没有「已验证域名」（决定能不能用自定义发件人）
  3) 能否真的把邮件投递到 lynneguo930@gmail.com

用法（PowerShell，在本文件所在目录，二选一）:
    $env:RESEND_API_KEY="re_你的key"; python .\\verify_resend.py
    python .\\verify_resend.py --key=re_你的key

可选:
    $env:RESEND_FROM="Literature Bot <bot@你的域名.com>"   # 有已验证域名时
    python .\\verify_resend.py --check-only                # 只验 Key/域名，不发信
    $env:RESEND_API_BASE="http://127.0.0.1:端口"           # 仅供本地自测

退出码: 0 = 全部通过 / 仅检查模式通过; 1 = 有问题，按屏幕提示处理
安全说明: Key 只放在内存与请求头里，不打印、不写文件、不落日志。
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

RECIPIENT = "lynneguo930@gmail.com"
DEFAULT_FROM = "onboarding@resend.dev"
TIMEOUT = 20

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


def out(msg: str = "") -> None:
    print(msg, flush=True)


def mask(key: str) -> str:
    return key[:3] + "*" * 6 + key[-4:] if len(key) > 12 else "***"


def read_key() -> str:
    key = os.environ.get("RESEND_API_KEY", "").strip()
    if not key:
        for arg in sys.argv[1:]:
            if arg.startswith("--key="):
                key = arg.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if key:
        return key
    # 刻意不做交互输入：Windows 下 getpass 会绕过 stdin 读控制台，容易假死。
    out("未检测到 RESEND_API_KEY。用下面任一方式提供后重新运行：")
    out('  方式一:  $env:RESEND_API_KEY="re_你的key"; python .\\verify_resend.py')
    out("  方式二:  python .\\verify_resend.py --key=re_你的key")
    return ""


def api(method: str, path: str, key: str, payload=None) -> tuple[int, object]:
    base = os.environ.get("RESEND_API_BASE", "https://api.resend.com").rstrip("/")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        base + path,
        data=body,
        method=method,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "resend-setup-check/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw)
        except ValueError:
            return exc.code, {"message": raw[:300]}
    except urllib.error.URLError as exc:
        return 0, {"message": "网络请求失败: %s" % exc.reason}
    except (ValueError, TimeoutError, OSError) as exc:
        return 0, {"message": "请求/响应异常: %s" % exc}


def err_msg(detail: object) -> str:
    if not isinstance(detail, dict):
        return str(detail)
    if detail.get("message"):
        return str(detail["message"])
    nested = detail.get("error")
    if isinstance(nested, dict) and nested.get("message"):
        return str(nested["message"])
    errors = detail.get("errors")
    if isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, dict):
            return str(first.get("message") or first)
    return json.dumps(detail, ensure_ascii=False)[:300]


def main() -> int:
    check_only = "--check-only" in sys.argv[1:]
    out("=" * 64)
    out("Resend 配置自检  |  目标收件人: " + RECIPIENT)
    out("=" * 64)

    key = read_key()
    if not key:
        out("[FAIL] 没有拿到 API Key，已退出。")
        return 1
    if not key.startswith("re_"):
        out("[提示] Key 通常以 re_ 开头，请确认复制完整（仍会继续尝试）。")
    out("已读取 API Key: " + mask(key))

    out("")
    out("[1/3] 验证 API Key 并查询已验证域名 ...")
    code, data = api("GET", "/domains", key)
    if code == 0:
        out("[FAIL] " + err_msg(data))
        out("       请检查网络 / 代理，或稍后重试。")
        return 1
    domain_message = err_msg(data).lower()
    if code in (401, 403) or (code == 400 and "api key" in domain_message):
        out("[FAIL] HTTP %d: %s" % (code, err_msg(data)))
        out("       Key 无效或权限不足。去 Resend -> API Keys 重新创建，")
        out("       Permission 选 Full access 或至少包含 Sending access。")
        return 1
    if code != 200:
        out("[FAIL] HTTP %d: %s" % (code, err_msg(data)))
        return 1

    domains = data.get("data") if isinstance(data, dict) else data
    domains = [d for d in domains if isinstance(d, dict)] if isinstance(domains, list) else []
    verified = [str(d.get("name")) for d in domains if d.get("status") == "verified"]
    out("[OK] API Key 有效。")
    if domains:
        for d in domains:
            out("     域名 %-32s 状态=%s" % (d.get("name"), d.get("status")))
    else:
        out("     账号下暂无域名（新账号正常现象）。")

    if verified:
        suggested = "Literature Bot <bot@%s>" % verified[0]
        out("     检测到已验证域名 -> 可用自定义发件人")
    else:
        suggested = DEFAULT_FROM
        out("     未检测到已验证域名 -> 只能用测试发件人")

    from_email = (os.environ.get("RESEND_FROM") or suggested).strip()
    out("")
    out("[2/3] 本次使用的发件人: " + from_email)
    if DEFAULT_FROM in from_email:
        out("       注意: onboarding@resend.dev 只能投递给「注册 Resend 账号的那个邮箱」。")
        out("       若注册邮箱不是 " + RECIPIENT + "，这一步大概率会失败。")

    if check_only:
        out("")
        out("--check-only: 跳过测试邮件。Key 与域名检查已完成。")
        out("建议填入 GitHub Secrets 的值:")
        out("   RESEND_API_KEY = (刚才那串 re_ 开头的 Key)")
        if from_email != DEFAULT_FROM:
            out("   RESEND_FROM   = " + from_email)
        return 0

    out("")
    out("[3/3] 发送 1 封测试邮件到 " + RECIPIENT + " ...")
    payload = {
        "from": from_email,
        "to": [RECIPIENT],
        "subject": "[配置自检] 文献速递测试邮件",
        "text": "这是一封配置自检邮件。看到它说明 Resend 可以正常投递到本邮箱。",
        "html": (
            "<div style=\"font-family:Arial,sans-serif;font-size:14px;line-height:1.7;\">"
            "<h2 style=\"font-size:16px;\">配置自检</h2>"
            "<p>这是一封配置自检邮件。看到它说明 Resend 可以正常投递到本邮箱，"
            "接下来可以把同样的值填进 GitHub Secrets 了。</p></div>"
        ),
    }
    code, data = api("POST", "/emails", key, payload)
    if (code == 200 or code == 201) or (isinstance(data, dict) and data.get("id")):
        email_id = data.get("id") if isinstance(data, dict) else "?"
        out("[OK] 发送成功，Resend id = " + str(email_id))
        out("")
        out("去邮箱查收（若无，检查「垃圾邮件 / 所有邮件 / 促销」分类）。")
        out("接下来把下面这些填进 GitHub 仓库 -> Settings -> Secrets and variables -> Actions:")
        out("   RESEND_API_KEY = (刚才那串 re_ 开头的 Key)")
        if from_email != DEFAULT_FROM:
            out("   RESEND_FROM   = " + from_email)
        out("   RECIPIENT_EMAIL / RESEND_FROM 不填也能跑（收件人已内置默认值）。")
        out("最后到 Actions -> Check Papers -> Run workflow 手动跑一次。")
        return 0

    message = err_msg(data)
    out("[FAIL] 发送失败 HTTP %s: %s" % (code, message))
    lowered = message.lower()
    if code == 403 or any(k in lowered for k in ("verify", "domain", "onboarding", "own email", "test")):
        out("")
        out("最常见原因：测试发件人只能发给注册 Resend 的那个邮箱，或不存在的域名。")
        out("解法 A（最省事）：用 " + RECIPIENT + " 注册 / 登录 Resend，再重跑本脚本。")
        out("解法 B：Resend -> Domains -> Add Domain，按提示在域名 DNS 后台加 3 条记录，")
        out("        等状态变为 Verified，然后设置 RESEND_FROM 后重跑本脚本。")
    elif code == 401 or (code == 400 and "api key" in lowered):
        out("Key 无效，去 Resend -> API Keys 重新生成并完整复制（re_ 开头）。")
    elif code == 429:
        out("触发限流，等 1 分钟再试；免费额度为每日 100 封 / 每秒 2 封。")
    elif code == 0:
        out("网络不通，检查代理/VPN 后重试。")
    else:
        out("把上面的错误信息发给助手，按提示逐项排查。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
