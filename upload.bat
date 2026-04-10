@echo off
echo ========================================
echo 申论判卷系统 - 一键上传脚本
echo ========================================
echo.

REM 检查是否在正确目录
if not exist "backend\app\main.py" (
    echo 错误：请确保在 E:\work2\全新网页版 目录运行此脚本
    pause
    exit /b 1
)

REM 第一步：删除不需要的大文件
echo 第一步：清理不需要的文件...
if exist "venv" (
    echo 删除 venv 文件夹（虚拟环境，不需要上传）
    rmdir /s /q venv 2>nul
)

if exist "__pycache__" (
    echo 删除 __pycache__ 缓存文件
    rmdir /s /q __pycache__ 2>nul
)

if exist "backend\app\__pycache__" (
    rmdir /s /q "backend\app\__pycache__" 2>nul
)

REM 第二步：初始化Git
echo.
echo 第二步：初始化Git仓库...
git init

REM 第三步：配置用户信息
echo.
echo 第三步：配置Git用户信息...
git config --global user.name "申论判卷系统"
git config --global user.email "shenlun@example.com"

REM 第四步：添加文件
echo.
echo 第四步：添加文件到Git...
git add .

REM 第五步：提交
echo.
echo 第五步：提交更改...
git commit -m "申论智能判卷系统 - 初始提交"

REM 第六步：询问GitHub仓库地址
echo.
echo 第六步：连接到GitHub仓库
set /p GITHUB_URL="请输入您的GitHub仓库地址（格式：https://github.com/用户名/仓库名.git）："

if "%GITHUB_URL%"=="" (
    echo 错误：未输入仓库地址
    pause
    exit /b 1
)

REM 第七步：连接到远程仓库
echo.
echo 连接到远程仓库：%GITHUB_URL%
git remote add origin "%GITHUB_URL%"

REM 第八步：推送代码
echo.
echo 第八步：推送代码到GitHub...
git push -u origin main

if errorlevel 1 (
    echo.
    echo 推送失败，尝试解决冲突...
    git pull origin main --allow-unrelated-histories
    git push -u origin main
)

echo.
echo ========================================
echo 上传完成！
echo 请访问您的GitHub仓库查看文件
echo ========================================
pause