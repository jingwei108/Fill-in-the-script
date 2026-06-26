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
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout

# ==================== 配置区 ====================
BASE_URL = "https://jw.hstc.edu.cn/eams/homeExt.action"
EVALUATE_LIST_URL = "https://jw.hstc.edu.cn/eams/teacherEvaluation!search.action"  # 可能需要根据实际地址调整

SUGGESTION_TEXT = "无"
LIANG_INDEX = 0  # 第几题填“良”，0表示第一题，-1表示最后一题，None表示随机
AUTO_SUBMIT = True
AUTO_NEXT = True
DELAY = 0.8


def sleep(seconds: float):
    time.sleep(seconds)


def is_login_page(page: Page) -> bool:
    """判断当前是否是登录页面"""
    return page.locator('input[name="username"], input[name="loginname"], #username').count() > 0


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


def navigate_to_evaluation_list(page: Page):
    """导航到量化评教列表页"""
    print("[步骤] 正在进入量化评教列表页...")
    # 先回到首页
    page.goto(BASE_URL)
    sleep(1)
    # 点击“量化评教”菜单（根据实际文字调整）
    try:
        page.locator('text=量化评教').first.click(timeout=5000)
        sleep(1)
        page.locator('text=量化评教').nth(1).click(timeout=5000)
    except PlaywrightTimeout:
        print("[警告] 未找到量化评教菜单，尝试直接访问列表地址")
        page.goto(EVALUATE_LIST_URL)
    sleep(2)


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


def click_radio_by_text(page: Page, text: str):
    """在页面上点击值为 text 的 radio（优/良/中/合格/不合格）"""
    # 策略1：label 文字匹配
    labels = page.locator('label').all()
    for label in labels:
        if (label.inner_text() or '').strip() == text:
            try:
                label.click(timeout=2000)
                return True
            except Exception:
                pass

    # 策略2：radio 的父元素文字匹配
    radios = page.locator('input[type="radio"]').all()
    for radio in radios:
        parent_text = ''
        try:
            parent = radio.locator('xpath=..')
            parent_text = (parent.inner_text() or '').strip()
        except Exception:
            pass
        if parent_text.startswith(text):
            try:
                radio.click(timeout=2000)
                return True
            except Exception:
                pass
    return False


def fill_suggestion(page: Page):
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
            el = page.locator(sel).first
            if el.is_visible(timeout=1000):
                el.fill(SUGGESTION_TEXT)
                return True
        except Exception:
            continue
    return False


def find_submit_button(page: Page):
    """查找提交按钮"""
    selectors = [
        'input[type="submit"]',
        'button[type="submit"]',
        'input[value*="提交"]',
        'input[value*="保存"]',
        'button:has-text("提交")',
        'button:has-text("保存")',
        'button:has-text("确定")',
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1000):
                return btn
        except Exception:
            continue
    return None


def fill_evaluation_page(page: Page):
    """在评教详情页执行填写"""
    print("[步骤] 正在填写评教表...")

    # 等待 radio 加载
    page.wait_for_selector('input[type="radio"]', timeout=10000)

    # 按 name 分组统计题目数量
    groups = {}
    radios = page.locator('input[type="radio"]').all()
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
        label = "良" if i == liang_idx else "优"
        # 优先通过 label 点击
        if not click_radio_by_text(page, label):
            # 兜底：通过 radio 父元素文字点击
            for radio in groups[name]:
                parent_text = ''
                try:
                    parent_text = (radio.locator('xpath=..').inner_text() or '').strip()
                except Exception:
                    pass
                if parent_text.startswith(label):
                    try:
                        radio.click()
                        break
                    except Exception:
                        pass
        sleep(0.1)

    # 填写建议
    fill_suggestion(page)
    print("[步骤] 填写完成")

    if AUTO_SUBMIT:
        sleep(DELAY)
        btn = find_submit_button(page)
        if btn:
            print("[步骤] 正在提交...")
            btn.click()
            # 等待提交结果，处理可能的确认弹窗
            sleep(2)
            handle_alert(page)
            return True
        else:
            print("[警告] 未找到提交按钮，请手动提交")
            return False
    return True


def handle_alert(page: Page):
    """处理提交后的确认弹窗"""
    try:
        dialog = page.wait_for_event('dialog', timeout=3000)
        if dialog:
            print(f"[弹窗] {dialog.message}")
            dialog.accept()
    except Exception:
        pass


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 必须可见，方便登录
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        try:
            page.goto(BASE_URL)

            # 如果未登录，等待用户登录
            if is_login_page(page):
                wait_for_login(page)

            # 进入量化评教列表
            navigate_to_evaluation_list(page)

            while True:
                links = get_unfinished_evaluation_links(page)
                if not links:
                    print("[完成] 所有课程已评教完毕")
                    break

                # 点击第一个待评教链接
                link = links[0]
                print(f"[步骤] 正在打开：{link['text']}")
                link['element'].click()
                sleep(2)

                # 填写并提交
                fill_evaluation_page(page)

                if not AUTO_NEXT:
                    break

                # 返回列表页
                sleep(1)
                navigate_to_evaluation_list(page)
                sleep(1)

        except Exception as e:
            print(f"[错误] {e}")
        finally:
            print("[提示] 脚本结束，浏览器保持打开，可手动关闭")
            # browser.close()  # 如需自动关闭，取消注释


if __name__ == '__main__':
    main()
