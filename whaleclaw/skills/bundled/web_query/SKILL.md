---
triggers:
  - 天气
  - 新闻
  - 价格
  - 汇率
  - 股票
  - 搜索
  - 查询
  - 今天
  - 最新
  - 实时
  - weather
  - news
  - price
  - search
  - 几度
  - 多少钱
max_tokens: 300
---

# 联网查询实时信息

## 触发条件

用户需要获取实时信息（天气、新闻、价格、汇率等）时触发。

## 指令

使用 bash 工具执行 curl 命令获取实时信息。

方式：
- 天气: curl "wttr.in/城市名?format=3" 或 curl "wttr.in/城市名?lang=zh"
- 网页内容: curl -s URL | 提取关键信息
- API 调用: curl 各类公开 API

也可以用 browser 工具浏览网页获取更详细的信息：
- browser(action="navigate", url="...")
- browser(action="get_text") 提取页面文本

## 示例

用户: 厦门今天几度
助手: bash(command="curl -s 'wttr.in/Xiamen?format=%C+%t'")
回复: 厦门今天 23°C，晴天。
