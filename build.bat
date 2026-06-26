@echo off
chcp 65001 >nul
echo 正在打包韩师评教助手...
pyinstaller --onefile --name "韩师评教助手" --console auto_evaluate_playwright.py
echo.
echo 打包完成，可执行文件位于 dist／韩师评教助手.exe
echo 按任意键退出...
pause >nul
