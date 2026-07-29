---
name: adgine/geo-media-publish
description: >
  将文章内容发布到用户本地浏览器已登录的社交媒体平台草稿箱（知乎 / 微信公众号 /
  百家号 / 头条号 / CSDN / 小红书 等），通过 Adgine 同步助手 Chrome 扩展完成，
  复用用户本地登录态，无需各平台开放 API。
  触发词：发布到知乎 / 发知乎草稿 / 同步到微信公众号 / 发公众号草稿 / 发布到百家号 /
  头条号草稿 / CSDN 草稿 / 小红书草稿 / GEO 社媒发布 / GEO 媒体发布 / geo media publish.
---

# GEO 媒体发布（社媒草稿箱）

把文章一键存进用户**本机 Chrome 已登录**的各平台草稿箱。无需用户在目标平台重新登录，
也不要求平台开放写 API —— **Adgine 同步助手**扩展复用本地浏览器的登录态，模拟人工存草稿。

## 运行前提（必读，手机端/纯云端不可用）

本 skill 通过 **用户本地 Chrome 浏览器** 发布，仅在满足以下全部条件的**桌面电脑**上可用：

- 本机已安装 **Adgine 同步助手** Chrome 扩展（默认已开启「媒体发布桥接」）
- 目标平台（知乎 / 微信 / 头条等）已在本机 Chrome 登录

> 手机端 / 纯云端 Agent（如 workbuddy 网页版）无法访问用户本地浏览器登录态，**本 skill 不可用**。
> 本地桥（`bridge-server.js`）会被脚本**按需自动拉起**；扩展与桥之间的 Token 在连接时**自动协商**，无需任何手动配置。

## 首次配置（零配置，开箱即用）

只需两步：

1. 在本机 Chrome 安装 **Adgine 同步助手** 扩展（「媒体发布桥接」默认开启，Token 自动协商，**无需复制任何密钥**）。
2. 在浏览器登录目标平台（如知乎）。

验证：`python3 scripts/check_login.py` 能列出平台登录态即配置成功。
（可选）桥端口被占用时设 `ADGINE_PUBLISH_PORT`（默认 9377）。

## Scripts

### 1) 检测登录态

```bash
python3 scripts/check_login.py                    # 全部平台
python3 scripts/check_login.py --platform zhihu   # 单个平台
```

发布前先确认目标平台显示「✓ 已登录」。

### 2) 发布到草稿箱

```bash
# 直接用本地文件
python3 scripts/save_draft.py --platform zhihu \
    --title "我的文章标题" --content-file ./article.md

# 从 GEO 云端内容库取（先用 adgine/geo-content 生成，需 GEO_API_KEY）
python3 scripts/save_draft.py --platform weixin --content-id <uuid>

# 可选：摘要 / 封面 / 标签
python3 scripts/save_draft.py --platform toutiao --title "标题" \
    --content-file ./a.md --summary "一句话" --tags "GEO,AI" 
```

**支持平台**（以扩展实际接入为准）：`zhihu` 知乎、`weixin` 微信公众号、`baijiahao` 百家号、
`toutiao` 头条号、`csdn` CSDN、`xiaohongshu` 小红书、`juejin` 掘金、`jianshu` 简书、
`bilibili` B 站专栏、`weibo` 微博、`sohu` 搜狐号、`douban` 豆瓣 等。用
`check_login.py` 查看本机可用平台与登录态。

成功后输出**草稿编辑链接**，发给用户即可到平台后台继续编辑/发布。

## 输出规则（与其他子技能一致）

- 列表/确认信息不展示原始 UUID，用平台中文名（如「知乎」「微信公众号」）。
- `--json` 模式原样输出脚本 JSON，便于调试。

## 工作流搭配

- 生成文章：`adgine/geo-content` → 拿到 `content_id` → 本 skill `--content-id` 发布
- 多平台分发：对同一 `content_id` 依次调用多次 `save_draft.py`（每个平台一次）

## 故障排除

- **「Chrome 扩展未连接」**：扩展没装 / 「媒体发布桥接」被关了。确认装了 Adgine 同步助手，并在扩展设置里把桥接开关打开（Token 会自动协商，无需手动配）。
- **端口被占用**：`ADGINE_PUBLISH_PORT` 换端口，或 `kill $(lsof -i :9377 -t)` 后重试。桥支持主备接管，重复拉起是安全的。
- **某平台存草稿失败/触发风控**：该平台（如知乎）风控较严，改用「复制全文带格式」手动粘贴；扩展只存草稿不直接发布即为规避风控。
