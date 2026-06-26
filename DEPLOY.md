# 国内部署方案

GitHub Pages 在国内访问较慢，下面提供几种更适合国内环境、门槛较低的部署方式。

---

## 方案一：本地单文件使用（零门槛，最快）

不需要任何服务器、账号或网络加速。直接把文件发给同学，双击就能用。

### 步骤

1. 进入项目 `release/` 文件夹
2. 里面有 `index.html` 和 `auto_evaluate.user.js` 两个文件
3. 把整个 `release` 文件夹压缩成 `zip` 发给同学
4. 同学解压后，双击 `index.html` 即可打开使用页面

### 优缺点

| 优点 | 缺点 |
|------|------|
| 完全不需要网络 | 不能在线更新 |
| 国内访问无限制 | 需要手动传播文件 |
| 最简单，适合小白 | 手机浏览器可能不方便 |

---

## 方案二：Cloudflare Pages（推荐，免费且稳定）

Cloudflare Pages 是全球 CDN，国内访问通常比 GitHub Pages 快，而且免费、部署简单。

### 步骤

1. 注册 [Cloudflare](https://dash.cloudflare.com/) 账号
2. 进入 **Pages** 服务
3. 选择 **Create a project**
4. 连接 GitHub 仓库（授权 Cloudflare 访问）
5. 构建设置：
   - Framework preset: **None**
   - Build command: 留空
   - Build output directory: `docs`
6. 点击 **Save and Deploy**
7. 部署完成后，Cloudflare 会给你一个 `.pages.dev` 的链接

### 自定义域名（可选）

如果你有自己的域名，可以在 Cloudflare Pages 里绑定，国内访问会更快。

---

## 方案三：腾讯云 CloudBase（国内访问最快）

腾讯云 CloudBase（云开发）提供静态网站托管，有免费额度，国内访问速度快。

### 步骤

1. 注册 [腾讯云账号](https://cloud.tencent.com/) 并完成实名认证
2. 进入 [CloudBase 控制台](https://console.cloud.tencent.com/tcb)
3. 创建一个新环境
4. 进入环境的 **静态网站托管**
5. 点击 **上传文件**，把 `docs/` 文件夹里的所有文件上传
6. 上传完成后，会有一个默认访问链接
7. 把这个链接发给同学即可

### 注意事项

- 需要实名认证
- 免费额度通常够用（每月有一定免费流量）
- 国内访问速度优秀

---

## 方案四：对象存储 + CDN（适合有域名的用户）

如果你已经有域名和阿里云/腾讯云账号，可以把静态网站托管到对象存储，并开启 CDN 加速。

### 可选服务

| 服务商 | 产品 |
|--------|------|
| 阿里云 | OSS + CDN |
| 腾讯云 | COS + CDN |
| 七牛云 | Kodo + CDN |
| 又拍云 | 云存储 + CDN |

### 大致步骤

1. 创建对象存储 bucket
2. 上传 `docs/` 文件夹内容
3. 开启静态网站托管
4. （可选）绑定自定义域名并开启 CDN
5. 分享访问链接

---

## 方案五：Vercel / Netlify（国外 CDN）

如果你熟悉国外服务，也可以使用 Vercel 或 Netlify 部署。

### 优缺点

| 优点 | 缺点 |
|------|------|
| 部署极其简单 | 国内访问不一定稳定 |
| 免费 | 可能需要梯子才能访问管理后台 |
| 自动 HTTPS | |

### Vercel 部署步骤

1. 注册 [Vercel](https://vercel.com/) 账号
2. Import GitHub 仓库
3. Framework Preset 选择 **Other**
4. Build Command 留空
5. Output Directory 填 `docs`
6. Deploy

---

## 方案对比

| 方案 | 难度 | 国内速度 | 是否需要账号 | 推荐度 |
|------|------|----------|--------------|--------|
| 本地单文件 | ⭐ | 最快 | 不需要 | ⭐⭐⭐⭐⭐ |
| Cloudflare Pages | ⭐⭐ | 较快 | 需要 | ⭐⭐⭐⭐ |
| 腾讯云 CloudBase | ⭐⭐⭐ | 最快 | 需要+实名 | ⭐⭐⭐⭐ |
| 对象存储+CDN | ⭐⭐⭐⭐ | 最快 | 需要+域名 | ⭐⭐⭐ |
| Vercel/Netlify | ⭐⭐ | 一般 | 需要 | ⭐⭐ |

---

## 推荐选择

| 需求 | 推荐方案 |
|------|----------|
| **最简单、最省心** | 本地单文件版，直接发压缩包 |
| **在线分享、国内访问快、免费** | **Cloudflare Pages**（本方案首选） |
| **在线分享、国内访问最快** | 腾讯云 CloudBase（需实名认证） |
| **长期维护、有自己的域名** | 对象存储 + CDN |

> 💡 **最佳组合**：静态页面用 **Cloudflare Pages**，脚本文件用 **jsDelivr CDN**（`cdn.jsdelivr.net`），这样页面和脚本在国内都有较好的访问速度。
