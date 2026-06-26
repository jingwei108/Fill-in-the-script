# 韩师量化评教助手（Python 版）

一键自动填写韩山师范学院教务系统量化评教：第一个评分题选 **“良”**，其余全部选 **“优”**，意见建议填 **“无”**。

本脚本使用 **Playwright** 自动化浏览器完成评教，无需安装浏览器扩展。

## 📋 环境要求

- Python 3.8+
- 已安装 Microsoft Edge 浏览器（脚本默认调用系统 Edge）

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/jingwei108/Fill-in-the-script.git
cd Fill-in-the-script
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

脚本默认使用系统已安装的 Microsoft Edge，无需额外下载浏览器。

### 3. 运行脚本

```bash
python auto_evaluate_playwright.py
```

运行后会自动打开浏览器并跳转到教务系统首页。

### 4. 手动登录

在打开的浏览器窗口中手动登录教务系统，登录成功后脚本会自动继续。

### 5. 等待完成

脚本会自动：
1. 进入量化评教列表
2. 逐个打开待评课程
3. 自动选择评分（一良其余优）
4. 填写意见建议“无”
5. 提交并继续下一门

## ⚙️ 配置说明

编辑 `auto_evaluate_playwright.py` 顶部的配置区：

```python
SUGGESTION_TEXT = "无"      # 建议内容
LIANG_INDEX = 0             # 第几题填“良”：0=第一题，-1=最后一题，None=随机
AUTO_SUBMIT = True          # 是否自动提交
AUTO_NEXT = True            # 是否自动继续下一门
DELAY = 0.8                 # 提交前等待秒数
```

## ⚠️ 注意事项

- 脚本运行时会打开真实浏览器窗口，方便登录和观察进度
- 所有操作均在本地完成，不会上传账号密码到任何服务器
- 评教前请确认当前学期评教已开放
- 建议先在一门课程上测试，确认无误后再批量使用
- 请合理使用，遵守学校相关规定

## 🛠️ 常见问题

**Q: 运行时报错 `ModuleNotFoundError: No module named 'playwright'`？**
A: 先执行 `pip install -r requirements.txt`。

**Q: 浏览器没打开？**
A: 脚本使用非无头模式，会调用系统 Edge。请确保电脑已安装 Edge；如需使用其他浏览器，修改 `auto_evaluate_playwright.py` 中的 `BROWSER_CHANNEL` 配置。

**Q: 登录后脚本没继续？**
A: 登录成功后页面会自动跳转，脚本检测到非登录页就会继续。如果长时间没反应，按回车或刷新页面。

**Q: 自动点击提交按钮没反应，但手动点击可以弹出确认框？**
A: 这是因为提交按钮 `#sub` 位于 iframe 内部，且它的点击事件是通过 `addEventListener` 绑定的，直接用 `el.click()` 或 Playwright 的 `click()` 无法触发。

当前版本已修复：脚本会切换到 iframe 的 document，dispatch 完整的鼠标事件（`mousedown` → `mouseup` → `click`）来触发提交；同时提前注册 `dialog` handler，自动接受提交后的确认弹窗，避免被 Playwright 默认 dismiss 而阻塞提交。
