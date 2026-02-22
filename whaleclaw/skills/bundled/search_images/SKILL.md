---
triggers:
  - 图片
  - 照片
  - 搜图
  - 找图
  - 壁纸
  - 头像
  - image
  - photo
  - picture
  - 下载图
max_tokens: 400
---

# 搜索并下载图片

## 触发条件

用户需要搜索、查找或下载图片时触发。

## 指令

使用 browser 工具的 search_images 动作来搜索并下载图片。

步骤：
1. 调用 browser 工具，action="search_images"，text="搜索关键词"
2. 图片会自动下载到本地，工具返回文件路径
3. 用 markdown 图片语法展示：![描述](返回的绝对路径)

注意：
- 搜索关键词用英文效果更好
- 如果第一次搜索没找到好的结果，可以换关键词重试
- 下载的图片保存在 ~/.whaleclaw/downloads/

## 示例

用户: 给我一张猫咪的照片
助手: 调用 browser(action="search_images", text="cute cat photo HD")
结果: 图片已下载: /Users/xxx/.whaleclaw/downloads/cute_cat_photo_HD_abc123.jpg
回复: ![可爱的猫咪](/Users/xxx/.whaleclaw/downloads/cute_cat_photo_HD_abc123.jpg)
