#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
韩山师范学院量化评教自动填写脚本
使用 Playwright 自动化浏览器

填写规则：
- 第一个评分题选"良"
- 其余评分题全部选"优"
- 意见建议填写"无"
- 自动提交并继续下一门

使用步骤：
1. 安装依赖：pip install playwright
2. 安装浏览器：playwright install chromium
3. 运行脚本，按提示先手动登录
4. 登录后脚本会自动处理评教
"""

import re
import time
import sys
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout

# ==================== 配置区 ====================
# 是否使用 WebVPN（如果你在校外且浏览器通过 webvpn.hstc.edu.cn 访问，就设为 True）
USE_WEBVPN = True
# WebVPN 前缀，把 jw.hstc.edu.cn 的地址套一层这个前缀
WEBVPN_PREFIX = "https://webvpn.hstc.edu.cn/https/77726476706e69737468656265737421fae00f9434246b1e7b0c9ce29b5b/"

# 教务系统首页，未登录时会被重定向到 CAS 登录页
BASE_URL = "https://jw.hstc.edu.cn/eams/homeExt.action"
# 学校的 CAS 统一认证登录页
CAS_LOGIN_URL = "https://hscas.hstc.edu.cn/cas/login"
# 量化评教列表地址（从底部状态栏观察到的实际地址）
EVALUATE_LIST_URL = "https://jw.hstc.edu.cn/eams/quality/stdEvaluate.action"


def to_webvpn_url(url: str) -> str:
    """把教务系统 URL 转成 WebVPN URL"""
    if not USE_WEBVPN:
        return url
    if url.startswith(WEBVPN_PREFIX):
        return url
    # 去掉 https://jw.hstc.edu.cn/ 前缀，换成 WebVPN 前缀
    if url.startswith("https://jw.hstc.edu.cn/"):
        return WEBVPN_PREFIX + url[len("https://jw.hstc.edu.cn/"):]
    if url.startswith("http://jw.hstc.edu.cn/"):
        return WEBVPN_PREFIX.replace("/https/", "/http/", 1) + url[len("http://jw.hstc.edu.cn/"):]
    return url


# 根据配置自动转换
BASE_URL = to_webvpn_url(BASE_URL)
CAS_LOGIN_URL = to_webvpn_url(CAS_LOGIN_URL)
EVALUATE_LIST_URL = to_webvpn_url(EVALUATE_LIST_URL)

SUGGESTION_TEXT = "无"
LIANG_INDEX = 0  # 第几题填“良”，0表示第一题，-1表示最后一题，None表示随机
AUTO_SUBMIT = True
AUTO_NEXT = True
DELAY = 0.8

# 浏览器选择："msedge" 使用系统 Edge，"chrome" 使用系统 Chrome，None 使用 Playwright 自带的 Chromium
BROWSER_CHANNEL = "msedge"


def sleep(seconds: float):
    time.sleep(seconds)


def is_login_page(page: Page) -> bool:
    """判断当前是否是登录页面（支持普通登录页和 CAS 登录页）"""
    url = page.url
    title = page.title() or ''

    # CAS 登录页特征
    if 'hscas.hstc.edu.cn' in url or 'cas/login' in url:
        return True
    if '统一身份认证' in title or 'CAS' in title or '登录' in title:
        return True

    # 普通登录页特征
    selectors = 'input[name="username"], input[name="loginname"], #username, input[name="user"], input[name="account"]'
    return page.locator(selectors).count() > 0


def check_network_access(page: Page) -> tuple[bool, bool]:
    """
    检查页面状态
    返回: (是否被拦截, 是否是登录页)
    """
    url = page.url
    title = page.title() or ''
    content = ''
    try:
        content = page.locator('body').inner_text(timeout=2000)
    except Exception:
        pass

    is_login = is_login_page(page)

    # 常见校园网拦截/403 提示
    blocked_keywords = ['访问策略禁止', '没有权限访问', '403', '访问被禁止', '校园网', '请连接 VPN']
    is_blocked = any(kw in title or kw in content for kw in blocked_keywords)

    if is_blocked:
        print("[警告] 当前页面被校园网拦截，尝试切换到 CAS 登录页")

    return is_blocked, is_login


def wait_for_login(page: Page, timeout: int = 120):
    """等待用户手动完成登录"""
    print("[提示] 请在浏览器中手动登录教务系统，登录成功后会自动继续...")
    start = time.time()
    while time.time() - start < timeout:
        if not is_login_page(page):
            print("[提示] 检测到已登录")
            return True
        sleep(1)
    raise TimeoutError("等待登录超时")


def _any_frame_has_evaluation_link(page: Page) -> bool:
    """检查 page 或任一 iframe 中是否已出现'进行评教'链接"""
    for ctx in [page] + list(page.frames):
        try:
            if ctx.locator('a:has-text("进行评教")').count() > 0:
                return True
        except Exception:
            pass
    return False


def _find_menu_by_playwright(ctx, text: str):
    """用 Playwright 定位器查找包含 text 的可见菜单元素"""
    # 方法1：语义化定位
    try:
        el = ctx.get_by_text(text).first
        if el.is_visible(timeout=2000):
            return el
    except Exception:
        pass

    # 方法2：多种 CSS 选择器兜底
    selectors = [
        f'header a:has-text("{text}")',
        f'.navbar a:has-text("{text}")',
        f'.nav a:has-text("{text}")',
        f'.el-menu a:has-text("{text}")',
        f'.menu a:has-text("{text}")',
        f'.topnav a:has-text("{text}")',
        f'a:has-text("{text}")',
        f'li:has-text("{text}")',
        f'span:has-text("{text}")',
        f'div:has-text("{text}")',
    ]
    for sel in selectors:
        try:
            el = ctx.locator(sel).first
            if el.is_visible(timeout=1500):
                return el
        except Exception:
            pass
    return None


def _click_menu_by_js(ctx, text: str) -> bool:
    """用 JS 直接查找并点击包含 text 的可见元素，不依赖 Playwright 定位"""
    try:
        clicked = ctx.evaluate(f'''() => {{
            const elements = Array.from(document.querySelectorAll('a, li, span, div, button'));
            for (const el of elements) {{
                if (el.textContent.trim().includes('{text}') && el.offsetParent !== null) {{
                    el.scrollIntoView({{block: 'center', behavior: 'instant'}});
                    el.dispatchEvent(new MouseEvent('mouseover', {{bubbles: true}}));
                    el.dispatchEvent(new MouseEvent('mousedown', {{bubbles: true}}));
                    el.dispatchEvent(new MouseEvent('mouseup', {{bubbles: true}}));
                    el.dispatchEvent(new MouseEvent('click', {{bubbles: true}}));
                    if (el.click) el.click();
                    return true;
                }}
            }}
            return false;
        }}''')
        return bool(clicked)
    except Exception:
        return False


def _click_hover_submenu(ctx, text: str) -> bool:
    """处理 hover 下拉菜单：先悬浮顶部菜单，再点击下拉项里的同名文字"""
    try:
        # 找到顶部菜单
        menu = _find_menu_by_playwright(ctx, text)
        if not menu:
            return False

        # 悬浮触发下拉，多等一会儿让下拉菜单渲染
        menu.hover(timeout=3000)
        sleep(2)

        # 方法1：找所有可见的同名元素，选择 y 坐标最大的（最靠下的下拉项）
        candidates = ctx.locator(f'text={text}').all()
        best = None
        best_y = -1
        for el in candidates:
            try:
                if not el.is_visible(timeout=1000):
                    continue
                box = el.bounding_box()
                if not box:
                    continue
                if box['y'] > best_y:
                    best_y = box['y']
                    best = el
            except Exception:
                continue

        if best:
            print(f"[信息] 点击下拉菜单项（方法1）...")
            best.scroll_into_view_if_needed(timeout=2000)
            best.click(timeout=5000)
            return True

        # 方法2：在下拉菜单容器中按文字查找
        submenu_selectors = [
            '.dropdown-menu',
            '.submenu',
            '.menu-list',
            '.el-dropdown-menu',
            '.el-menu--popup',
            '.nav-submenu',
            '.dropdown',
        ]
        for container_sel in submenu_selectors:
            try:
                container = ctx.locator(container_sel).first
                if container.is_visible(timeout=1500):
                    el = container.locator(f'text={text}').first
                    if el.is_visible(timeout=1500):
                        print(f"[信息] 点击下拉菜单项（方法2: {container_sel}）...")
                        el.scroll_into_view_if_needed(timeout=2000)
                        el.click(timeout=5000)
                        return True
            except Exception:
                continue

        return False
    except Exception:
        return False


def _click_hover_submenu_by_js(ctx, text: str) -> bool:
    """用 JS 直接处理 hover 下拉菜单：悬浮顶部菜单，点击最下方的下拉项"""
    try:
        clicked = ctx.evaluate(f'''() => {{
            const all = Array.from(document.querySelectorAll('a, li, span, div, button'));
            const candidates = all.filter(el => el.textContent.trim() === '{text}' && el.offsetParent !== null);
            if (candidates.length === 0) return false;

            // 按垂直位置排序，最上面的是顶部菜单，最下面的是下拉项
            candidates.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
            const topMenu = candidates[0];
            const subMenu = candidates[candidates.length - 1];

            // 悬浮顶部菜单
            topMenu.dispatchEvent(new MouseEvent('mouseover', {{bubbles: true}}));
            topMenu.dispatchEvent(new MouseEvent('mouseenter', {{bubbles: true}}));

            // 延迟点击下拉项
            setTimeout(() => {{
                subMenu.scrollIntoView({{block: 'center', behavior: 'instant'}});
                subMenu.dispatchEvent(new MouseEvent('mouseover', {{bubbles: true}}));
                subMenu.dispatchEvent(new MouseEvent('mousedown', {{bubbles: true}}));
                subMenu.dispatchEvent(new MouseEvent('mouseup', {{bubbles: true}}));
                subMenu.dispatchEvent(new MouseEvent('click', {{bubbles: true}}));
                if (subMenu.click) subMenu.click();
            }}, 500);

            return true;
        }}''')
        sleep(1.5)  # 等待 setTimeout 执行
        return bool(clicked)
    except Exception:
        return False


def _click_hover_submenu_by_mouse(page: Page, text: str) -> bool:
    """用真实鼠标移动来处理 hover 下拉菜单：移动到顶部菜单，再移动到下拉项点击"""
    try:
        # 找到顶部菜单
        menu = _find_menu_by_playwright(page, text)
        if not menu:
            return False

        box = menu.bounding_box()
        if not box:
            return False

        # 移动鼠标到顶部菜单中心，触发 hover
        cx = box['x'] + box['width'] / 2
        cy = box['y'] + box['height'] / 2
        page.mouse.move(cx, cy)
        sleep(1.5)  # 等待下拉菜单渲染

        # 查找下拉项：所有可见的同名元素中 y 坐标最大的
        candidates = page.locator(f'text={text}').all()
        best = None
        best_y = -1
        for el in candidates:
            try:
                if not el.is_visible(timeout=1000):
                    continue
                box2 = el.bounding_box()
                if not box2:
                    continue
                # 排除顶部菜单本身（y 坐标接近）
                if abs(box2['y'] - box['y']) < 10:
                    continue
                if box2['y'] > best_y:
                    best_y = box2['y']
                    best = el
            except Exception:
                continue

        if best:
            box2 = best.bounding_box()
            sx = box2['x'] + box2['width'] / 2
            sy = box2['y'] + box2['height'] / 2
            page.mouse.move(sx, sy)
            sleep(0.5)
            page.mouse.click(sx, sy)
            print(f"[信息] 已用鼠标点击下拉菜单项")
            return True

        return False
    except Exception:
        return False


def navigate_to_evaluation_list(page: Page):
    """导航到量化评教列表页"""
    print("[步骤] 正在进入量化评教列表页...")

    # 方法0：直接访问评教列表 URL（最可靠）
    try:
        print(f"[信息] 尝试直接跳转评教列表: {EVALUATE_LIST_URL}")
        page.goto(EVALUATE_LIST_URL, wait_until='networkidle')
        sleep(2)
        if _any_frame_has_evaluation_link(page):
            print("[信息] 已直接跳转到量化评教列表")
            return
        else:
            print("[警告] 直接跳转后未找到评教链接，回到首页尝试点击菜单")
    except Exception as e:
        print(f"[警告] 直接跳转失败: {e}")

    # 回到首页，准备点击菜单
    page.goto(BASE_URL, wait_until='networkidle')
    sleep(2)

    clicked = False

    # 方法1：真实鼠标移动处理 hover 下拉菜单
    print("[信息] 尝试用鼠标移动点击 hover 下拉菜单...")
    if _click_hover_submenu_by_mouse(page, "量化评教"):
        clicked = True
    else:
        for idx, frame in enumerate(page.frames):
            if _click_hover_submenu_by_mouse(frame, "量化评教"):
                print(f"[信息] 已在 frame[{idx}] 中用鼠标点击下拉菜单")
                clicked = True
                break

    # 方法2：JS 处理 hover 下拉菜单
    if not clicked:
        print("[信息] 尝试用 JS 点击 hover 下拉菜单...")
        if _click_hover_submenu_by_js(page, "量化评教"):
            clicked = True
        else:
            for idx, frame in enumerate(page.frames):
                if _click_hover_submenu_by_js(frame, "量化评教"):
                    print(f"[信息] 已在 frame[{idx}] 中用 JS 点击下拉菜单")
                    clicked = True
                    break

    # 方法3：Playwright 处理 hover 下拉菜单
    if not clicked:
        print("[信息] 尝试用 Playwright 点击 hover 下拉菜单...")
        if _click_hover_submenu(page, "量化评教"):
            clicked = True
        else:
            for idx, frame in enumerate(page.frames):
                if _click_hover_submenu(frame, "量化评教"):
                    print(f"[信息] 已在 frame[{idx}] 中点击下拉菜单")
                    clicked = True
                    break

    # 方法4：普通 Playwright 点击主页面菜单
    if not clicked:
        menu = _find_menu_by_playwright(page, "量化评教")
        if menu:
            try:
                print("[信息] 点击顶部'量化评教'菜单...")
                menu.scroll_into_view_if_needed(timeout=2000)
                menu.click(timeout=5000)
                clicked = True
            except Exception as e:
                print(f"[警告] Playwright 点击菜单失败: {e}")

    # 方法5：普通 Playwright 点击 iframe 中的菜单
    if not clicked:
        for idx, frame in enumerate(page.frames):
            menu = _find_menu_by_playwright(frame, "量化评教")
            if menu:
                try:
                    print(f"[信息] 在 frame[{idx}] 中点击'量化评教'菜单...")
                    menu.scroll_into_view_if_needed(timeout=2000)
                    menu.click(timeout=5000)
                    clicked = True
                    break
                except Exception as e:
                    print(f"[警告] 在 frame[{idx}] 点击菜单失败: {e}")

    # 方法6：JS 强制点击兜底
    if not clicked:
        print("[信息] 尝试用 JS 强制点击菜单...")
        if _click_menu_by_js(page, "量化评教"):
            clicked = True
        else:
            for idx, frame in enumerate(page.frames):
                if _click_menu_by_js(frame, "量化评教"):
                    print(f"[信息] 已在 frame[{idx}] 中用 JS 点击菜单")
                    clicked = True
                    break

    # 等待评教列表加载，最多等 12 秒
    if clicked:
        print("[信息] 等待评教列表加载...")
        for _ in range(12):
            sleep(1)
            if _any_frame_has_evaluation_link(page):
                break

    # 检查结果
    if _any_frame_has_evaluation_link(page):
        print("[信息] 已成功进入量化评教列表")
    elif clicked:
        print("[警告] 菜单点击后未找到'进行评教'链接，可能是 AJAX 加载问题")
        print("[提示] 请在浏览器中手动点击'量化评教'菜单，然后按回车键继续...")
        input()
    else:
        print("[错误] 无法自动点击菜单")
        print("[提示] 请在浏览器中手动点击'量化评教'菜单，然后按回车键继续...")
        input()


def find_evaluation_frame(page: Page):
    """找到包含'进行评教'链接的 frame"""
    sleep(2)
    frames = list(page.frames)
    for idx, frame in enumerate(frames):
        try:
            count = frame.locator('a:has-text("进行评教")').count()
            if count > 0:
                print(f"[信息] 在 frame[{idx}] 中找到 {count} 个'进行评教'链接，后续操作在此 frame 中执行")
                return frame
        except Exception:
            pass
    return page


def get_unfinished_evaluation_links(ctx):
    """获取列表页中所有未评教的链接"""
    # 先等 AJAX 加载
    sleep(2)

    all_links = []
    try:
        # 尝试多种选择器
        selectors = [
            'a:has-text("进行评教")',
        ]
        for sel in selectors:
            elements = ctx.locator(sel).all()
            if elements:
                print(f"[信息] 用选择器 '{sel}' 找到 {len(elements)} 个链接")
                for el in elements:
                    try:
                        href = el.get_attribute('href') or ''
                        text = el.inner_text() or ''
                        all_links.append({'element': el, 'href': href, 'text': text})
                    except Exception:
                        pass
                break
    except Exception:
        pass

    # 去重
    seen = set()
    unique_links = []
    for link in all_links:
        key = link['text'] + link['href']
        if key not in seen:
            seen.add(key)
            unique_links.append(link)

    if not unique_links:
        print("[信息] 未发现待评教课程，可能已评教完毕或页面结构不同")

    print(f"[信息] 总共发现 {len(unique_links)} 门待评教课程")
    return unique_links


def get_unfinished_evaluation_links(page: Page):
    """获取列表页中所有未评教的链接"""
    links = []
    # 查找包含“进行评教”的 <a> 标签
    elements = page.locator('a:has-text("进行评教")').all()
    for el in elements:
        href = el.get_attribute('href') or ''
        text = el.inner_text() or ''
        links.append({'element': el, 'href': href, 'text': text})
    print(f"[信息] 发现 {len(links)} 门待评教课程")
    return links


def click_radio_by_text(ctx, text: str):
    """在页面上点击值为 text 的 radio（优/良/中/合格/不合格）"""
    text = text.strip()
    # 策略1：label 文字匹配（label 里直接包含文字）
    labels = ctx.locator('label').all()
    for label in labels:
        label_text = (label.inner_text() or '').strip()
        if label_text == text or label_text.startswith(text):
            try:
                label.click(timeout=2000)
                return True
            except Exception:
                pass

    # 策略2：label 的 for 属性对应 radio 的 id
    radios = ctx.locator('input[type="radio"]').all()
    for radio in radios:
        try:
            radio_id = radio.get_attribute('id') or ''
            if radio_id:
                label = ctx.locator(f'label[for="{radio_id}"]').first
                if label.is_visible(timeout=1000):
                    label_text = (label.inner_text() or '').strip()
                    if label_text == text or label_text.startswith(text):
                        label.click(timeout=2000)
                        return True
        except Exception:
            pass

    # 策略3：radio 的父元素或祖先元素文字匹配
    for radio in radios:
        parent_text = ''
        try:
            # 尝试父元素、祖父元素
            for ancestor in ['xpath=..', 'xpath=../..', 'xpath=../../..']:
                parent = radio.locator(ancestor)
                parent_text = (parent.inner_text() or '').strip()
                if parent_text and text in parent_text:
                    break
        except Exception:
            pass
        if text in parent_text:
            try:
                # 点击 label 而不是 radio，更容易触发页面事件
                parent = radio.locator('xpath=..')
                if text in (parent.inner_text() or '').strip():
                    parent.click(timeout=2000)
                else:
                    radio.click(timeout=2000)
                return True
            except Exception:
                pass
    return False


def fill_suggestion(ctx):
    """填写意见建议"""
    selectors = [
        'textarea[name*="suggest"]',
        'textarea[name*="advice"]',
        'textarea[name*="opinion"]',
        'textarea[name*="remark"]',
        'textarea[name*="comment"]',
        'textarea',
        'input[name*="suggest"]',
        'input[name*="advice"]',
    ]
    for sel in selectors:
        try:
            el = ctx.locator(sel).first
            if el.is_visible(timeout=1000):
                el.fill(SUGGESTION_TEXT)
                # 触发 input 和 change 事件，确保表单验证通过
                el.evaluate('''el => {
                    el.value = arguments[1];
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                    el.dispatchEvent(new Event('blur', {bubbles: true}));
                }''', SUGGESTION_TEXT)
                el.blur()
                print(f"[信息] 已填写建议：{SUGGESTION_TEXT}")
                return True
        except Exception:
            continue
    return False


def find_submit_button(ctx):
    """查找提交按钮"""
    selectors = [
        '#sub',  # 你们学校提交按钮的 id
        'input[type="submit"]',
        'button[type="submit"]',
        'input[value*="提交"]',
        'input[value*="保存"]',
        'input[value*="确定"]',
        'button:has-text("提交")',
        'button:has-text("保存")',
        'button:has-text("确定")',
        'a:has-text("提交")',
        'a:has-text("保存")',
        'a:has-text("确定")',
        '.btn:has-text("提交")',
        '.btn:has-text("保存")',
        '.btn:has-text("确定")',
    ]

    for sel in selectors:
        try:
            btn = ctx.locator(sel).first
            if btn.is_visible(timeout=1000):
                return btn
        except Exception:
            continue
    return None


def fill_evaluation_page(ctx, page: Page):
    """在评教详情页执行填写"""
    print("[步骤] 正在填写评教表...")

    # 等待 radio 加载
    ctx.wait_for_selector('input[type="radio"]', timeout=10000)

    # 按 name 分组统计题目数量
    groups = {}
    radios = ctx.locator('input[type="radio"]').all()
    for radio in radios:
        name = radio.get_attribute('name') or ''
        if name not in groups:
            groups[name] = []
        groups[name].append(radio)

    group_names = [k for k, v in groups.items() if len(v) > 0]
    total = len(group_names)
    if total == 0:
        print("[错误] 未找到评分题目")
        return False

    print(f"[信息] 共 {total} 道评分题")

    # 确定哪题填“良”
    if LIANG_INDEX is None:
        liang_idx = __import__('random').randint(0, total - 1)
    elif LIANG_INDEX < 0:
        liang_idx = total + LIANG_INDEX
    else:
        liang_idx = LIANG_INDEX
    liang_idx = max(0, min(liang_idx, total - 1))

    for i, name in enumerate(group_names):
        target = "良" if i == liang_idx else "优"
        target_value = "1" if target == "良" else "0"
        radios_in_group = groups[name]
        clicked = False

        # 方法1：在组内按 value 点击 radio
        for radio in radios_in_group:
            try:
                val = (radio.get_attribute('value') or '').strip()
                if val == target_value:
                    radio.scroll_into_view_if_needed(timeout=2000)
                    radio.click(timeout=2000)
                    # 触发 change 事件，确保页面记录选择
                    try:
                        radio.evaluate('''el => {
                            el.checked = true;
                            el.dispatchEvent(new Event('change', {bubbles: true}));
                            el.dispatchEvent(new Event('input', {bubbles: true}));
                            el.dispatchEvent(new Event('click', {bubbles: true}));
                        }''')
                    except Exception:
                        pass
                    clicked = True
                    break
            except Exception:
                pass

        # 方法2：在组内按文字点击 label
        if not clicked:
            for radio in radios_in_group:
                try:
                    radio_id = radio.get_attribute('id') or ''
                    if radio_id:
                        label = ctx.locator(f'label[for="{radio_id}"]').first
                        label_text = (label.inner_text() or '').strip()
                        if label_text == target or label_text.startswith(target):
                            label.scroll_into_view_if_needed(timeout=2000)
                            label.click(timeout=2000)
                            clicked = True
                            break
                except Exception:
                    pass

        if clicked:
            print(f"[信息] 第 {i+1}/{total} 题已选'{target}'")
        else:
            print(f"[警告] 第 {i+1}/{total} 题未能选择'{target}'")
        sleep(0.1)

    # 填写建议
    fill_suggestion(ctx)
    print("[步骤] 填写完成")

    if AUTO_SUBMIT:
        sleep(DELAY)
        # 滚动到页面底部，让提交按钮可见
        try:
            ctx.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            sleep(1)
        except Exception:
            pass

        # 提交前强制刷新所有 radio 和 textarea 状态
        try:
            ctx.evaluate('''() => {
                // 触发所有 radio 的 click/change
                document.querySelectorAll('input[type="radio"]:checked').forEach(r => {
                    r.dispatchEvent(new Event('click', {bubbles: true}));
                    r.dispatchEvent(new Event('change', {bubbles: true}));
                });
                // 触发 textarea 的 blur
                document.querySelectorAll('textarea').forEach(t => {
                    t.dispatchEvent(new Event('blur', {bubbles: true}));
                });
            }''')
            sleep(1)
        except Exception:
            pass

        # 提交前检查：统计已选 radio 数量
        try:
            checked_count = ctx.evaluate('''() => document.querySelectorAll('input[type="radio"]:checked').length''')
            total_radios = ctx.evaluate('''() => document.querySelectorAll('input[type="radio"]').length''')
            print(f"[信息] 提交前检查：已选 {checked_count}/{total_radios} 个 radio")
        except Exception:
            pass

        btn = find_submit_button(ctx)
        if btn:
            print("[步骤] 正在提交...")
            try:
                btn.scroll_into_view_if_needed(timeout=2000)
            except Exception:
                pass

            # 提前注册 dialog handler，避免确认弹窗被 Playwright 默认 dismiss
            alert_state = register_alert_handler(page)
            try:
                # 方法1：直接通过 JS 在 iframe document 中点击 #sub
                # 注意：#sub 是 type="button"，事件是通过 addEventListener 绑定的
                # 所以要用 dispatchEvent 触发，不能只用 el.click()
                click_success = False
                try:
                    result = ctx.evaluate('''() => {
                        const sub = document.querySelector('#sub');
                        if (sub) {
                            sub.focus();
                            sub.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
                            sub.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window}));
                            sub.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                            return 'dispatched';
                        }
                        return 'not_found';
                    }''')
                    click_success = (result == 'dispatched')
                except Exception:
                    pass

                # 方法2：用 Playwright 的 click 兜底
                if not click_success:
                    try:
                        btn.click()
                        click_success = True
                    except Exception:
                        pass

                # 等待弹窗出现并被 handler 处理，再等待页面响应
                sleep(3)
            finally:
                unregister_alert_handler(page, alert_state)
            return click_success
        else:
            print("[警告] 未找到提交按钮，请手动提交")
            return False
    return True


def register_alert_handler(page: Page):
    """注册 dialog handler，返回状态对象供 unregister_alert_handler 使用。

    Playwright 默认会自动 dismiss dialog；只要 handler 存在，
    Playwright 就会把控制权交给 handler，不再自动 dismiss。
    """
    state = {'accepted': False, 'messages': []}

    def handler(dialog):
        state['messages'].append(dialog.message)
        print(f"[弹窗] {dialog.type}: {dialog.message}")
        try:
            dialog.accept()
            state['accepted'] = True
        except Exception:
            pass

    page.on('dialog', handler)
    state['handler'] = handler
    return state


def unregister_alert_handler(page: Page, state):
    """移除 dialog handler 并打印处理结果"""
    page.remove_listener('dialog', state['handler'])
    if state['messages']:
        print(f"[信息] 已处理 {len(state['messages'])} 个弹窗")
    return state['accepted'], state['messages']


def main():
    with sync_playwright() as p:
        # 根据配置选择浏览器：msedge / chrome / 默认 chromium
        launch_kwargs = {
            'headless': False,  # 必须可见，方便登录
        }
        if BROWSER_CHANNEL:
            launch_kwargs['channel'] = BROWSER_CHANNEL
            print(f"[信息] 使用系统浏览器: {BROWSER_CHANNEL}")
        else:
            print("[信息] 使用 Playwright 内置 Chromium")

        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        try:
            # 先访问教务首页
            print(f"[步骤] 正在打开: {BASE_URL}")
            page.goto(BASE_URL, wait_until='networkidle')
            sleep(2)

            blocked, logged_in = check_network_access(page)

            # 如果被校园网拦截，尝试打开 CAS 登录页
            if blocked:
                print(f"[步骤] 尝试打开 CAS 登录页: {CAS_LOGIN_URL}")
                page.goto(CAS_LOGIN_URL, wait_until='networkidle')
                sleep(2)
                blocked, logged_in = check_network_access(page)

            # 如果当前是登录页，等待用户手动登录
            if not logged_in or is_login_page(page):
                print("[信息] 当前是登录页，等待手动登录...")
                wait_for_login(page)
            else:
                print("[信息] 检测到已登录，继续执行")

            # 进入量化评教列表
            navigate_to_evaluation_list(page)

            # 找到包含评教链接的 frame
            eval_ctx = find_evaluation_frame(page)

            while True:
                links = get_unfinished_evaluation_links(eval_ctx)
                if not links:
                    print("[完成] 所有课程已评教完毕")
                    break

                # 点击第一个待评教链接
                link = links[0]
                print(f"[步骤] 正在打开：{link['text']}")
                link['element'].click()
                sleep(3)

                # 填写并提交（在相同 frame 中执行）
                fill_evaluation_page(eval_ctx, page)

                if not AUTO_NEXT:
                    break

                # 等待页面自动跳转回列表页
                print("[步骤] 等待页面自动跳转回列表...")
                waited = 0
                submit_success = False
                while waited < 30:
                    sleep(1)
                    current_url = eval_ctx.url
                    body_text = ''
                    try:
                        body_text = eval_ctx.locator('body').inner_text(timeout=1000)
                    except Exception:
                        pass

                    # 判断提交成功：URL 变回列表，或页面出现成功/评教完成提示
                    if 'answer' not in current_url and 'stdEvaluate' not in current_url:
                        print("[信息] 已自动返回列表页")
                        submit_success = True
                        break
                    if any(kw in body_text for kw in ['提交成功', '评教完成', '保存成功', '成功', '完成']):
                        print(f"[信息] 检测到成功提示：{body_text[:100]}")
                        submit_success = True
                        sleep(2)
                        break
                    waited += 1

                # 如果还在详情页，暂停
                if not submit_success:
                    print("[警告] 提交后仍在详情页，可能提交失败")
                    print("[提示] 请检查页面状态，按回车键继续或关闭浏览器...")
                    input()

                # 刷新 frame 引用
                eval_ctx = find_evaluation_frame(page)

        except Exception as e:
            print(f"[错误] {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("[提示] 脚本结束，浏览器保持打开，可手动关闭")
            input("[提示] 按回车键关闭浏览器...")
            browser.close()


if __name__ == '__main__':
    main()
