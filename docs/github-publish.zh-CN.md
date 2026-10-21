# PaperVisual：GitHub 上传与安装指南

本项目的公开品牌为 **PaperVisual**，建议 GitHub 仓库名 `papervisual`，Skill 路径 `skills/papervisual`。请注意：本说明是本地发布步骤，**没有代替你在 GitHub 创建仓库或推送**。示例 GitHub 用户名是 `KuoYuan-ame`，如果你的用户名不是这个，需要替换。

## 1. 解压发布包

将 `papervisual-github-ready-v0.1.0.zip` 解压到独立目录。请进入包含 `README.md`、`pyproject.toml`、`skills/`、`src/` 的 `papervisual/` 文件夹，再在资源管理器地址栏输入 `powershell`。

**不要**在 Windows 用户主目录（例如 PowerShell 中的 `$HOME`） 等用户主目录执行 `git init` 或 `git add -A`。

在 PowerShell 里确认当前目录：

```powershell
Get-Location
Test-Path .\skills\papervisual\SKILL.md
```

第二条应为 `True`。

## 2. 创建 GitHub 空仓库

在 https://github.com/new 创建名为 `papervisual` 的 **Public** 仓库。仓库已包含 README、LICENSE 和 .gitignore；创建时不要勾选自动添加这些文件。

建议简介：`AI-assisted graphical abstracts and editable visual summaries for research papers.`

## 3. 提交并推送

在确认 `Get-Location` 位于项目文件夹、Skill 路径存在之后执行：

```powershell
git init -b main
git add -A
git status
git commit -m "Initial release: PaperVisual v0.1.0"
git remote add origin https://github.com/KuoYuan-ame/papervisual.git
git push -u origin main
```

**在 `git status` 看见任何 `AppData`、用户文档、缓存或非项目文件时，立即停止，不要继续提交。** 如果远程仓库早已设置了 `origin`，先使用 `git remote -v` 检查并按需执行 `git remote set-url origin <正确URL>`，不要重复添加。

## 4. 发布 v0.1.0

先在 GitHub **Actions** 页面确认 CI 成功，再执行：

```powershell
git tag v0.1.0
git push origin v0.1.0
```

此仓库内的 `.github/workflows/release.yml` 会在 tag 推送时尝试发布 Release，生成 `papervisual-skill.zip`、Python 源码/安装包及校验文件，并使用 `docs/releases/v0.1.0.md` 作为发布说明。不要同时手动创建同名 Release。发布结果以 Actions 的实际执行情况为准。

## 5. 安装和使用 Skill

在支持 Agent Skills 的客户端中，从仓库的 `skills/papervisual` 文件夹安装。**Skill 名称是 `papervisual`**；安装后可尝试按客户端支持的方式调用 `$papervisual`。

不用安装客户端时，也可直接解压独立 Skill ZIP，并运行 `python /你的绝对路径/papervisual/scripts/papervisual.py` 加正常的命令参数，前提是机器安装了 Python 3.10+。PNG/PDF 还需要相应可选依赖。

命令行 CLI 安装后使用 `papervisual render ...`；旧命令 `paperfig render ...` 仍保留兼容。`PAPERFIG_API_KEY` 维持原名。

## 注意

当前版本不会直接读取 PDF/DOCX，也不会独立验证论文结论。生成的图稿必须经人工校对；自动测试通过不等于投稿验收通过。
