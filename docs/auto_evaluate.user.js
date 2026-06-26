// ==UserScript==
// @name         韩师量化评教自动填写
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  自动填写量化评教：第一个评分题填“良”，其余填“优”，建议填“无”
// @author       You
// @match        https://jw.hstc.edu.cn/eams/*
// @downloadURL  https://cdn.jsdelivr.net/gh/jingwei108/Fill-in-the-script@main/docs/auto_evaluate.user.js
// @updateURL    https://cdn.jsdelivr.net/gh/jingwei108/Fill-in-the-script@main/docs/auto_evaluate.user.js
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    // ==================== 配置区 ====================
    const CONFIG = {
        suggestionText: '无',     // 建议内容
        liangIndex: 0,            // 第几题填“良”：0=第一题，-1=最后一题，null=随机
        autoSubmit: true,         // 是否自动提交
        autoNext: true,           // 是否自动继续下一门
        delay: 800                // 提交前等待毫秒
    };

    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

    // ==================== 调试日志 ====================
    function log(msg) {
        console.log('[自动评教] ' + msg);
    }

    // ==================== 页面判断 ====================
    function isListPage() {
        const links = document.querySelectorAll('a');
        for (const a of links) {
            if ((a.textContent || '').includes('进行评教')) return true;
        }
        return false;
    }

    function isEvaluatePage() {
        const radios = document.querySelectorAll('input[type="radio"]');
        return radios.length >= 3;
    }

    // ==================== 点击 radio ====================
    function clickRadioByText(text) {
        // 策略1：label 文字匹配
        const labels = document.querySelectorAll('label');
        for (const label of labels) {
            if (label.textContent.trim() === text) {
                const input = label.querySelector('input[type="radio"]') ||
                              (label.htmlFor ? document.getElementById(label.htmlFor) : null);
                if (input && !input.checked) {
                    input.click();
                    return true;
                }
            }
        }

        // 策略2：radio 的父元素或兄弟文本匹配
        const radios = document.querySelectorAll('input[type="radio"]');
        for (const radio of radios) {
            const parent = radio.parentElement;
            if (parent) {
                const txt = parent.textContent.trim();
                if (txt.startsWith(text) || txt === text) {
                    if (!radio.checked) {
                        radio.click();
                        return true;
                    }
                }
            }
            // 策略3：radio 后面的文本节点
            const next = radio.nextSibling;
            if (next && next.nodeType === 3 && next.textContent.trim() === text) {
                if (!radio.checked) {
                    radio.click();
                    return true;
                }
            }
        }
        return false;
    }

    // ==================== 填写建议 ====================
    function fillSuggestion() {
        const selectors = [
            'textarea', 'input[type="text"]',
            'input[name*="suggest"]', 'input[name*="advice"]', 'input[name*="opinion"]',
            'textarea[name*="suggest"]', 'textarea[name*="advice"]', 'textarea[name*="opinion"]'
        ];
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) {
                const hint = (el.placeholder + el.name + el.id + '').toLowerCase();
                if (el.tagName === 'TEXTAREA' || hint.includes('suggest') || hint.includes('advice') || hint.includes('opinion') || hint.includes('remark') || hint.includes('意见') || hint.includes('建议')) {
                    el.value = CONFIG.suggestionText;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    log('已填写建议：' + CONFIG.suggestionText);
                    return true;
                }
            }
        }
        log('未找到建议输入框');
        return false;
    }

    // ==================== 获取题目分组 ====================
    function getQuestionGroups() {
        const map = {};
        document.querySelectorAll('input[type="radio"]').forEach(r => {
            const name = r.name;
            if (!name) return;
            if (!map[name]) map[name] = [];
            map[name].push(r);
        });
        return Object.values(map).filter(g => g.length >= 2);
    }

    // ==================== 查找提交按钮 ====================
    function findSubmitButton() {
        const selectors = [
            'input[type="submit"]', 'button[type="submit"]',
            'input[value*="提交"]', 'input[value*="保存"]', 'input[value*="确定"]',
            'button', 'input[type="button"]'
        ];
        for (const sel of selectors) {
            const elements = document.querySelectorAll(sel);
            for (const el of elements) {
                const text = (el.value || el.textContent || '').trim();
                if (text.includes('提交') || text.includes('保存') || text.includes('确定')) {
                    return el;
                }
            }
        }
        return null;
    }

    // ==================== 处理弹窗 ====================
    function acceptDialogs() {
        // 尝试点击常见的确认按钮（layui/alert 等）
        const selectors = [
            '.layui-layer-btn0', '.layui-layer-btn1',
            '.ui-dialog-buttonpane button', '.dialog-confirm',
            'button:contains("确定")', 'button:contains("是")',
            'input[value="确定"]', 'input[value="是"]'
        ];
        for (const sel of selectors) {
            try {
                const el = document.querySelector(sel);
                if (el && el.offsetParent !== null) {
                    el.click();
                    log('点击弹窗按钮：' + (el.value || el.textContent));
                    return true;
                }
            } catch (e) {}
        }
        return false;
    }

    // ==================== 详情页填写 ====================
    async function fillEvaluationPage() {
        log('进入评教详情页，开始填写');
        await sleep(500);

        const groups = getQuestionGroups();
        if (groups.length === 0) {
            alert('[自动评教] 未找到评分题目，请检查页面');
            return;
        }
        log(`找到 ${groups.length} 道评分题`);

        // 确定哪题填“良”
        let liangIdx;
        if (CONFIG.liangIndex === null) {
            liangIdx = Math.floor(Math.random() * groups.length);
        } else if (CONFIG.liangIndex < 0) {
            liangIdx = groups.length + CONFIG.liangIndex;
        } else {
            liangIdx = CONFIG.liangIndex;
        }
        liangIdx = Math.max(0, Math.min(liangIdx, groups.length - 1));
        log(`第 ${liangIdx + 1} 题将填“良”，其余填“优”`);

        for (let i = 0; i < groups.length; i++) {
            const label = i === liangIdx ? '良' : '优';
            if (!clickRadioByText(label)) {
                // 兜底：按同 name 的 radio 顺序点击
                const radios = groups[i];
                const target = radios.find(r => {
                    const t = (r.parentElement?.textContent || r.nextSibling?.textContent || r.value || '').trim();
                    return t === label;
                });
                if (target && !target.checked) target.click();
            }
            await sleep(50);
        }

        fillSuggestion();
        log('评分填写完成');

        if (CONFIG.autoSubmit) {
            await sleep(CONFIG.delay);
            const btn = findSubmitButton();
            if (btn) {
                log('点击提交按钮');
                btn.click();
                await sleep(1500);
                acceptDialogs();
            } else {
                alert('[自动评教] 已填写完成，但未找到提交按钮');
            }
        }
    }

    // ==================== 列表页：一键评教 ====================
    async function startBatchEvaluation() {
        log('开始批量评教');
        const links = Array.from(document.querySelectorAll('a')).filter(a =>
            (a.textContent || '').includes('进行评教')
        );
        if (links.length === 0) {
            alert('[自动评教] 当前页面没有“进行评教”链接');
            return;
        }
        log(`发现 ${links.length} 门待评课程`);

        for (let i = 0; i < links.length; i++) {
            log(`正在打开第 ${i + 1}/${links.length} 门课程`);
            links[i].click();
            // 等待页面变成详情页
            let waited = 0;
            while (!isEvaluatePage() && waited < 50) {
                await sleep(200);
                waited++;
            }
            if (isEvaluatePage()) {
                await fillEvaluationPage();
                // 等待提交完成并返回列表
                await sleep(2500);
                while (isEvaluatePage() && waited < 50) {
                    await sleep(500);
                    waited++;
                }
            } else {
                log('等待详情页超时，跳过');
            }
        }
        log('批量评教完成');
    }

    // ==================== 添加悬浮按钮 ====================
    function addFloatingButton() {
        if (document.getElementById('hstc-evaluate-helper')) return;

        const container = document.createElement('div');
        container.id = 'hstc-evaluate-helper';
        container.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 999999;
            display: flex;
            flex-direction: column;
            gap: 8px;
        `;

        function makeBtn(text, color, onClick) {
            const btn = document.createElement('button');
            btn.textContent = text;
            btn.style.cssText = `
                padding: 10px 16px;
                background: ${color};
                color: #fff;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                cursor: pointer;
                box-shadow: 0 2px 8px rgba(0,0,0,0.25);
                font-weight: bold;
            `;
            btn.onclick = onClick;
            return btn;
        }

        container.appendChild(makeBtn('一键自动评教', '#ff5722', () => {
            if (isListPage()) {
                startBatchEvaluation();
            } else if (isEvaluatePage()) {
                fillEvaluationPage();
            } else {
                alert('[自动评教] 未识别到评教页面，请进入“量化评教”列表或评教详情页');
            }
        }));

        container.appendChild(makeBtn('调试：输出页面信息', '#2196f3', () => {
            log('当前URL：' + location.href);
            log('列表页判断：' + isListPage());
            log('详情页判断：' + isEvaluatePage());
            log('radio数量：' + document.querySelectorAll('input[type="radio"]').length);
            log('进行评教链接数：' + document.querySelectorAll('a').length);
            const sample = Array.from(document.querySelectorAll('a')).filter(a => (a.textContent || '').includes('进行评教')).slice(0, 3);
            sample.forEach((a, i) => log(`链接${i + 1}：${a.textContent.trim()}`));
            alert('页面信息已输出到控制台（按 F12 查看）');
        }));

        document.body.appendChild(container);
        log('悬浮按钮已添加');
    }

    // ==================== 主入口 ====================
    function init() {
        log('脚本已加载，当前URL：' + location.href);
        addFloatingButton();

        if (isEvaluatePage()) {
            log('检测到评教详情页，自动填写');
            fillEvaluationPage();
        } else if (isListPage()) {
            log('检测到评教列表页');
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
