@echo off
REM ================================
REM make_latex_model 验证脚本 (Windows)
REM ================================
REM
REM 使用方法:
REM   validate.bat --project NSFC_Young
REM   validate.bat --project projects\NSFC_Young
REM   validate.bat --help
REM ================================

setlocal enabledelayedexpansion

REM 默认配置
set DEFAULT_PROJECT=NSFC_Young
set SCRIPT_DIR=%~dp0
set SKILL_DIR=%SCRIPT_DIR%..
set BASE_DIR=%SKILL_DIR%\..\..

REM 解析参数
set PROJECT=
set TEMPLATE=

:parse_args
if "%~1"=="" goto end_parse
if "%~1"=="--project" (
    set PROJECT=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--template" (
    set TEMPLATE=%~2
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
if "%PROJECT:~0,1%"=="\" goto absolute_path
if "%PROJECT:~1,1%"==":" goto absolute_path
if "%PROJECT:~0,1%"=="." goto relative_path

REM 纯项目名称
set PROJECT_PATH=%BASE_DIR%\projects\%PROJECT%
goto found_path

:relative_path
set PROJECT_PATH=%BASE_DIR%\%PROJECT%
goto found_path

:absolute_path
set PROJECT_PATH=%PROJECT%
goto found_path

:found_path

REM 转换为绝对路径
pushd "%PROJECT_PATH%" 2>nul
if errorlevel 1 (
    echo 错误: 项目路径不存在: %PROJECT_PATH%
    exit /b 1
)
set PROJECT_PATH=%CD%
popd

REM 配置文件路径
set CONFIG=%PROJECT_PATH%\extraTex\@config.tex
set MAIN_TEX=%PROJECT_PATH%\main.tex
set SKILL_MD=%SKILL_DIR%\SKILL.md
set CONFIG_YAML=%SKILL_DIR%\config.yaml

REM 计数器
set PASS_COUNT=0
set WARN_COUNT=0
set FAIL_COUNT=0

echo ========================================
echo   make_latex_model 验证报告
echo ========================================
echo.
echo 测试时间: %date% %time%
echo 项目路径: %PROJECT_PATH%
echo 模板: %TEMPLATE%
echo.

REM ========================================
REM 第一优先级：基础编译检查
REM ========================================
echo ========================================
echo 第一优先级：基础编译检查
echo ========================================
echo.

REM 检查项目目录
if exist "%PROJECT_PATH%" (
    call :pass "项目目录存在: %PROJECT_PATH%"
) else (
    call :fail "项目目录不存在: %PROJECT_PATH%"
)

REM 检查配置文件
if exist "%CONFIG%" (
    call :pass "配置文件存在: @config.tex"
) else (
    call :fail "配置文件不存在: @config.tex"
)

REM 检查主文件
if exist "%MAIN_TEX%" (
    call :pass "主文件存在: main.tex"
) else (
    call :fail "主文件不存在: main.tex"
)

REM 检查编译产物
if exist "%PROJECT_PATH%\main.pdf" (
    call :pass "编译成功: main.pdf 存在"
) else (
    call :fail "编译失败: main.pdf 不存在"
)

REM 检查技能文档
if exist "%SKILL_MD%" (
    call :pass "技能文档存在: SKILL.md"
) else (
    call :fail "技能文档不存在: SKILL_MD"
)

REM ========================================
REM 第二优先级：样式参数一致性
REM ========================================
echo.
echo ========================================
echo 第二优先级：样式参数一致性
echo ========================================
echo.

REM 检查行距设置
findstr /C:"baselinestretch" "%CONFIG%" >nul 2>&1
if errorlevel 1 (
    call :fail "行距设置: 未找到 baselinestretch 定义"
) else (
    call :pass "行距设置: 已找到 baselinestretch"
)

REM 检查颜色定义
findstr /C:"definecolor{MsBlue}" "%CONFIG%" >nul 2>&1
if errorlevel 1 (
    call :fail "颜色定义: 未找到 MsBlue 定义"
) else (
    call :pass "颜色定义: 已找到 MsBlue"
)

REM 检查页面设置
findstr /C:"geometry" "%CONFIG%" >nul 2>&1
if errorlevel 1 (
    call :warn "页面边距: 未找到明确的 geometry 设置"
) else (
    call :pass "页面设置: 已找到 geometry"
)

REM ========================================
REM 总结
REM ========================================
echo.
echo ========================================
echo 验证总结
echo ========================================
echo.

set /a TOTAL_CHECKS=%PASS_COUNT%+%WARN_COUNT%+%FAIL_COUNT%

echo 总检查项: %TOTAL_CHECKS%
echo   通过: %PASS_COUNT%
echo   警告: %WARN_COUNT%
echo   失败: %FAIL_COUNT%
echo.

if %FAIL_COUNT%==0 (
    echo [OK] 所有核心检查通过！
    if %WARN_COUNT% GTR 0 (
        echo 但有 %WARN_COUNT% 个警告需要注意
    )
    exit /b 0
) else (
    echo [ERROR] 有 %FAIL_COUNT% 个检查失败，需要修复
    exit /b 1
)

REM 子程序
:pass
echo [OK] %~1
set /a PASS_COUNT+=1
goto :eof

:warn
echo [WARN] %~1
set /a WARN_COUNT+=1
goto :eof

:fail
echo [FAIL] %~1
set /a FAIL_COUNT+=1
goto :eof

:help
echo 用法: %~nx0 [OPTIONS]
echo.
echo 选项:
echo   --project PATH    项目路径或名称
echo   --template NAME   模板名称
echo   --help, -h        显示帮助
echo.
echo 示例:
echo   %~nx0 --project NSFC_Young
echo   %~nx0 --project projects\NSFC_Young
exit /b 0
