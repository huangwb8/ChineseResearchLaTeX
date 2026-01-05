@echo off
REM ================================
REM make_latex_model 一键式优化 (Windows)
REM ================================

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set SKILL_DIR=%SCRIPT_DIR%..
set BASE_DIR=%SKILL_DIR%\..\..
set PYTHON_SCRIPT=%SCRIPT_DIR%optimize.py

REM 默认配置
set DEFAULT_PROJECT=NSFC_Young
set PROJECT=
set INTERACTIVE=
set REPORT=

REM 解析参数
:parse_args
if "%~1"=="" goto end_parse
if "%~1"=="--project" (
    set PROJECT=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--interactive" (
    set INTERACTIVE=--interactive
    shift
    goto parse_args
)
if "%~1"=="-i" (
    set INTERACTIVE=--interactive
    shift
    goto parse_args
)
if "%~1"=="--report" (
    set REPORT=--report %~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--help" goto help
if "%~1"=="-h" goto help
echo 错误: 未知参数 %~1
goto help

:end_parse

REM 如果未指定项目，使用默认项目
if "%PROJECT%"=="" set PROJECT=%DEFAULT_PROJECT%

REM 解析项目路径
if exist "%BASE_DIR%\projects\%PROJECT%" (
    set PROJECT_PATH=%BASE_DIR%\projects\%PROJECT%
) else (
    set PROJECT_PATH=%PROJECT%
)

pushd "%PROJECT_PATH%" 2>nul
if errorlevel 1 (
    echo 错误: 项目路径不存在: %PROJECT_PATH%
    exit /b 1
)
set PROJECT_PATH=%CD%
popd

REM 检查 Python 脚本
if not exist "%PYTHON_SCRIPT%" (
    echo 错误: Python 脚本不存在: %PYTHON_SCRIPT%
    exit /b 1
)

echo ========================================
echo   LaTeX 模板一键优化
echo ========================================
echo.
echo 项目: %PROJECT_PATH%
echo 模式: %INTERACTIVE:~1%=自动%
echo.

python "%PYTHON_SCRIPT%" --project "%PROJECT_PATH%" %INTERACTIVE% %REPORT%

echo.
echo ========================================
echo   优化完成
echo ========================================

goto :eof

:help
echo 用法: %~nx0 [OPTIONS]
echo.
echo 选项:
echo   --project PATH      项目路径或名称
echo   --interactive, -i   交互模式
echo   --report PATH       生成报告文件
echo   --help, -h          显示帮助
echo.
echo 示例:
echo   %~nx0 --project NSFC_Young
echo   %~nx0 --project NSFC_Young --interactive
exit /b 0
