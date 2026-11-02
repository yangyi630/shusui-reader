@echo off
chcp 65001 >nul
title 书髓 - 后端服务

echo.
echo ========================================
echo    书髓 - 跨平台阅读精华聚合
echo    后端服务启动脚本
echo ========================================
echo.

cd /d "%~dp0"

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist "venv" (
    echo [信息] 正在创建虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [错误] 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo [信息] 虚拟环境创建完成
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 检查依赖
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [信息] 正在安装依赖包...
    echo.
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo [错误] 依赖安装失败，请检查网络连接
        echo 可以尝试切换国内镜像源:
        echo   pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
        echo.
        pause
        exit /b 1
    )
    echo.
    echo [信息] 依赖安装完成
)

REM 生成图标
if not exist "..\icons\icon-192.png" (
    echo.
    echo [信息] 正在生成应用图标...
    python generate_icons.py
)

REM 获取本机 IP 地址
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set IP=%%a
    set IP=!IP: =!
    goto :found_ip
)
set IP=127.0.0.1
:found_ip

echo.
echo ========================================
echo   ✓ 服务启动中...
echo.
echo   本机访问: http://127.0.0.1:5000
echo   局域网访问: http://%IP%:5000
echo.
echo   按 Ctrl+C 停止服务
echo ========================================
echo.

REM 启动服务
python server.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 服务启动失败，错误代码: %errorlevel%
    echo.
)

pause
