# Git 极简使用指南（Windows版）

## 第一步：安装Git
1. 下载：https://git-scm.com/download/win
2. 运行安装程序，全部点"Next"
3. 安装完成后，重启电脑

## 第二步：验证Git安装
1. 按 `Win + R`，输入 `cmd`，回车
2. 输入命令：`git --version`
3. 应该显示类似：`git version 2.45.0.windows.1`

## 第三步：Git基本命令

### 1. 初始化仓库（在项目文件夹）
```bash
cd E:\work2\全新网页版
git init
```
**注意**：是 `init`，不是 `inti`

### 2. 配置用户名和邮箱（只需一次）
```bash
git config --global user.name "您的名字"
git config --global user.email "您的邮箱"
```

### 3. 添加所有文件
```bash
git add .
```
**注意**：`.` 表示当前目录所有文件

### 4. 提交文件
```bash
git commit -m "第一次提交：申论判卷系统"
```

### 5. 连接到GitHub仓库
```bash
git remote add origin https://github.com/您的用户名/shenlun-judge-system.git
```

### 6. 推送代码
```bash
git push -u origin main
```

## 常见错误解决

### 错误1：`git: 'inti' is not a git command`
**原因**：拼写错误
**解决**：使用 `git init`（正确拼写）

### 错误2：`fatal: not a git repository`
**原因**：不在Git仓库目录
**解决**：
```bash
cd E:\work2\全新网页版
git init
```

### 错误3：`fatal: remote origin already exists`
**原因**：已经设置过远程仓库
**解决**：
```bash
git remote remove origin
git remote add origin https://github.com/您的用户名/shenlun-judge-system.git
```

### 错误4：`failed to push some refs`
**原因**：GitHub仓库有README文件
**解决**：
```bash
git pull origin main --allow-unrelated-histories
git push -u origin main
```

## 快速命令清单
```bash
# 1. 进入项目目录
cd E:\work2\全新网页版

# 2. 初始化
git init

# 3. 添加文件
git add .

# 4. 提交
git commit -m "申论判卷系统"

# 5. 连接远程
git remote add origin https://github.com/您的用户名/shenlun-judge-system.git

# 6. 推送
git push -u origin main
```

## 如果还是不会，使用这个备用方案
创建一个批处理文件 `upload.bat`，内容如下：
```batch
@echo off
cd /d "E:\work2\全新网页版"
git init
git add .
git commit -m "申论判卷系统"
git remote add origin https://github.com/您的用户名/shenlun-judge-system.git
git push -u origin main
pause
```
保存后双击运行。