# 期货盯控看板

基于天勤行情 API 的期货量价/技术面盯控看板。

当前版本只做量价和技术面分析，暂不接入消息面、基本面、宏观和 EDB 数据。

## 运行

复制配置模板：

```bash
cp .env.example .env
```

在 `.env` 中填写本地天勤账号密码：

```bash
TQ_ACCOUNT=你的天勤账号
TQ_PASSWORD=你的天勤密码
```

启动服务：

```bash
PORT=8011 python3 server.py
```

打开浏览器：

```text
http://127.0.0.1:8011
```

## 文件结构

```text
server.py              # 启动入口
src/                   # 后端核心逻辑
static/index.html      # 前端页面
docs/                  # 项目思路和交接文档
data/                  # 本地缓存，不提交
.env                   # 本地密钥，不提交
```

## 安全说明

`.env`、`data/`、`__pycache__/` 和 `.DS_Store` 已加入 `.gitignore`，不要提交真实账号、密码或本地缓存。
