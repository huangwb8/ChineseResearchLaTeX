@echo off
REM ================================
REM make_latex_model 性能基准测试 (Windows)
REM ================================

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set SKILL_DIR=%SCRIPT_DIR%..
set BASE_DIR=%SKILL_DIR%\..\..
set PROJECT=%~1

if "%PROJECT%"=="" set PROJECT=NSFC_Young

echo ========================================
echo   性能基准测试
echo ========================================
echo.
echo 项目: %PROJECT%
echo.

REM 设置项目路径
if exist "%BASE_DIR%\projects\%PROJECT%" (
    set PROJECT_PATH=%BASE_DIR%\projects\%PROJECT%
) else (
    set PROJECT_PATH=%PROJECT%
)

echo 工作目录: %PROJECT_PATH%
echo.

REM 测试编译时间
echo 测试编译性能...
cd /d "%PROJECT_PATH%"

echo [1/3] 清理旧文件...
del /q main.aux main.bbl main.blg main.log main.out main.pdf 2>nul

echo [2/3] 编译 LaTeX...
echo %time% > compile_time.txt
xelatex -interaction=nonstopmode main.tex >nul 2>&1
if errorlevel 1 (
    echo 编译失败
    goto :eof
)
echo %time% >> compile_time.txt

echo [3/3] 获取文件大小...
for %%F in (main.pdf) do set PDF_SIZE=%%~zF

echo.
echo ========================================
echo 测试结果
echo ========================================
echo.
echo PDF 文件大小: %PDF_SIZE% bytes
echo.

REM 显示编译时间
echo 编译时间:
type compile_time.txt
echo.

del /q compile_time.txt

echo 测试完成
