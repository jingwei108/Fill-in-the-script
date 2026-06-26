# 韩师量化评教助手

一键自动填写韩山师范学院教务系统量化评教：第一个评分题选 **“良”**，其余全部选 **“优”**，意见建议填 **“无”**。

## 🌐 在线使用（推荐）

本项目已做成静态网站，小白只需点几下即可使用：

👉 **[点击访问在线页面](https://你的-cloudflare-pages域名.pages.dev/)**

> 本项目推荐部署在 **Cloudflare Pages**，国内访问比 GitHub Pages 更快。脚本文件通过 **jsDelivr CDN** 分发，更新速度快。
>
> 其他方案（本地单文件、腾讯云 CloudBase、OSS+CDN）请看 [`DEPLOY.md`](DEPLOY.md)。

页面提供三种使用方式：
1. **一键安装 Tampermonkey 脚本** — 最自动化
2. **拖拽书签小工具到书签栏** — 无需安装扩展
3. **复制控制台代码** — 应急使用

## 📁 项目结构

```
Fill in the script/
├── docs/                       # 静态网站（适合 Cloudflare Pages / GitHub Pages）
│   ├── index.html              # 在线使用页面
│   ├── style.css               # 页面样式
│   ├── main.js                 # 页面交互（复制控制台代码等）
│   └── auto_evaluate.user.js   # Tampermonkey 脚本
├── release/                    # 本地单文件版（可直接发给同学）
│   ├── index.html              # 内联了 CSS/JS 的独立网页
│   └── auto_evaluate.user.js   # Tampermonkey 脚本
├── auto_evaluate_tampermonkey.js   # 脚本源码
├── auto_evaluate_playwright.py     # Python 自动化脚本
├── DESIGN_PLAN.md                # 设计计划
├── DEPLOY.md                       # 国内部署方案
└── README.md                       # 本说明
```

## 🚀 部署到 Cloudflare Pages（推荐，国内访问更快）

### 方法一：GitHub Actions 自动部署（已配置）

项目已包含自动部署工作流 `.github/workflows/deploy-cloudflare-pages.yml`，push 到 `main` 分支后会自动部署。

#### 配置步骤

1. 注册 [Cloudflare](https://dash.cloudflare.com/) 账号
2. 进入 Cloudflare 控制台右侧的 **API Tokens**，点击 **Create Token**
3. 选择 **Custom token**，权限设置：
   - **Zone:Read**（可选，用于自定义域名）
   - **Cloudflare Pages:Edit**
4. 在 GitHub 仓库进入 **Settings → Secrets and variables → Actions**
5. 添加两个仓库秘密：
   - `CLOUDFLARE_API_TOKEN`：上面创建的 API Token
   - `CLOUDFLARE_ACCOUNT_ID`：Cloudflare 控制台右侧显示的 Account ID
6. 在 Cloudflare Pages 创建一个项目，项目名建议为 `Fill-in-the-script`
7. 以后每次 push 到 `main` 分支，GitHub Actions 会自动部署

### 方法二：Cloudflare Pages 直接连接 GitHub（更简单）

1. 注册 [Cloudflare](https://dash.cloudflare.com/) 账号
2. 进入 **Pages** 服务，选择 **Create a project**
3. 连接本 GitHub 仓库
4. 构建设置：
   - Framework preset: **None**
   - Build command: 留空
   - Build output directory: `docs`
5. 点击 **Save and Deploy**

### 自定义域名（可选）

如果你有自己的域名，绑定到 Cloudflare Pages 后国内访问会更快更稳定。

### 部署完成后

把 `https://你的-project-name.pages.dev/` 替换到本 README 和页面中的链接。

## 💻 本地预览网站

如果你想在本地预览生成的静态页面：

```bash
cd docs
# 方式1：Python 3
python -m http.server 8000

# 方式2：Node.js
npx serve

# 方式3：VS Code 安装 Live Server 插件，右键 index.html 选择 Open with Live Server
```

然后浏览器访问 `http://localhost:8000`。

## 🛠️ 开发说明

### 修改脚本

编辑 `docs/auto_evaluate.user.js` 或根目录的 `auto_evaluate_tampermonkey.js`，修改后把根目录的同步复制到 `docs/` 下：

```bash
cp auto_evaluate_tampermonkey.js docs/auto_evaluate.user.js
```

### 修改网页内容

直接编辑 `docs/index.html` 和 `docs/style.css` 即可。

## ⚠️ 安全提示

- 所有脚本均在本地浏览器运行，不会上传账号密码
- 建议先在一门课程上测试，确认无误后再批量使用
- 请合理使用，遵守学校相关规定
