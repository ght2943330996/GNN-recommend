@echo off
chcp 65001 >nul
echo ============================================================
echo   旅游景点推荐系统 - 分步启动
echo ============================================================
echo.

cd /d "%~dp0"

echo 步骤 1: 检查依赖...
python -c "import flask" 2>nul
if errorlevel 1 (
    echo Flask 未安装
    echo 正在安装依赖...
    pip install -r src\backend\requirements.txt
) else (
    echo 依赖已安装
)
echo.

echo 步骤 2: 初始化项目...
python scripts\setup.py
echo.

echo 步骤 3: 启动后端服务...
echo 后端将在新窗口中启动
start "后端服务" cmd /k "cd /d %~dp0 && cd src\backend && python app.py"
echo 后端启动中...
timeout /t 5 /nobreak >nul
echo.

echo 步骤 4: 启动前端服务...
echo 前端将在新窗口中启动
start "前端服务" cmd /k "cd /d %~dp0 && cd src\frontend && python -m http.server 8080"
echo 前端启动中...
timeout /t 3 /nobreak >nul
echo.

echo ============================================================
echo   服务启动完成！
echo ============================================================
echo   后端地址: http://localhost:5000
echo   前端地址: http://localhost:8080
echo   健康检查: http://localhost:5000/api/health
echo ============================================================
echo.
echo 提示:
echo   - 在浏览器中打开 http://localhost:8080 访问系统
echo   - 关闭命令行窗口即可停止服务
echo   - 如遇到问题，请查看各个窗口的错误信息
echo ============================================================
echo.

echo 正在打开浏览器...
timeout /t 3 /nobreak >nul
start http://localhost:8080

pause
