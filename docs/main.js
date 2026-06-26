const consoleScript = `(function() {
    const SUGGESTION = '无';
    const LIANG_INDEX = 0;

    function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

    function clickByText(text) {
        for (const label of document.querySelectorAll('label')) {
            if (label.textContent.trim() === text) {
                const input = label.querySelector('input[type="radio"]') || document.getElementById(label.htmlFor);
                if (input && !input.checked) { input.click(); return true; }
            }
        }
        for (const r of document.querySelectorAll('input[type="radio"]')) {
            const t = (r.parentElement?.textContent || r.nextSibling?.textContent || '').trim();
            if (t === text && !r.checked) { r.click(); return true; }
        }
        return false;
    }

    async function run() {
        const groups = {};
        document.querySelectorAll('input[type="radio"]').forEach(r => {
            if (!r.name) return;
            if (!groups[r.name]) groups[r.name] = [];
            groups[r.name].push(r);
        });
        const names = Object.keys(groups).filter(k => groups[k].length >= 2);
        console.log('共 ' + names.length + ' 道题');

        let liang = LIANG_INDEX;
        if (liang < 0) liang = names.length + liang;
        for (let i = 0; i < names.length; i++) {
            clickByText(i === liang ? '良' : '优');
            await sleep(50);
        }

        for (const el of document.querySelectorAll('textarea, input[type="text"]')) {
            const hint = (el.placeholder + el.name + el.id).toLowerCase();
            if (el.tagName === 'TEXTAREA' || hint.includes('意见') || hint.includes('建议') || hint.includes('suggest') || hint.includes('advice')) {
                el.value = SUGGESTION;
                el.dispatchEvent(new Event('input', {bubbles:true}));
                break;
            }
        }

        await sleep(500);
        for (const el of document.querySelectorAll('input[type="submit"], button[type="submit"], input[type="button"], button')) {
            const text = (el.value || el.textContent || '').trim();
            if (text.includes('提交') || text.includes('保存') || text.includes('确定')) {
                console.log('点击提交：' + text);
                el.click();
                return;
            }
        }
        alert('未找到提交按钮，请手动提交');
    }

    run();
})();`;

const bookmarkletCode = `(function(){const S='无',L=0;function c(t){for(const l of document.querySelectorAll('label'))if(l.textContent.trim()===t){const i=l.querySelector('input[type=radio]')||document.getElementById(l.htmlFor);if(i&&!i.checked){i.click();return true}}for(const r of document.querySelectorAll('input[type=radio]')){const p=(r.parentElement?r.parentElement.textContent:'')||(r.nextSibling?r.nextSibling.textContent:'')||'';if(p.trim()===t&&!r.checked){r.click();return true}}return false}const g={};document.querySelectorAll('input[type=radio]').forEach(r=>{if(!r.name)return;g[r.name]=g[r.name]||[];g[r.name].push(r)});const n=Object.keys(g).filter(k=>g[k].length>=2);let li=L;if(li<0)li=n.length+li;for(let i=0;i<n.length;i++)c(i===li?'良':'优');for(const e of document.querySelectorAll('textarea,input[type=text]')){const h=(e.placeholder||'')+(e.name||'')+(e.id||'');if(e.tagName==='TEXTAREA'||h.toLowerCase().includes('意见')||h.toLowerCase().includes('建议')){e.value=S;e.dispatchEvent(new Event('input',{bubbles:true}));break}}setTimeout(()=>{for(const b of document.querySelectorAll('input[type=submit],button[type=submit],input[type=button],button')){const t=(b.value||b.textContent||'').trim();if(t.includes('提交')||t.includes('保存')||t.includes('确定')){b.click();return}}alert('未找到提交按钮')},500);})();`;

function copyConsoleScript() {
    navigator.clipboard.writeText(consoleScript).then(() => {
        const tip = document.getElementById('copy-tip');
        tip.textContent = '✅ 已复制到剪贴板，去控制台粘贴吧！';
        setTimeout(() => tip.textContent = '', 3000);
    }).catch(() => {
        const tip = document.getElementById('copy-tip');
        tip.textContent = '❌ 复制失败，请手动选择代码复制';
    });
}

// 页面加载后生成书签链接
document.addEventListener('DOMContentLoaded', () => {
    const bm = document.getElementById('bookmarklet');
    if (bm) {
        bm.href = 'javascript:' + bookmarkletCode;
    }
});
