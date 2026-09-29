@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title VOA-SUL ERP
color 0B

cd /d "%~dp0"

:: ------------------------------------------------------------------
:: BANCO COMPARTILHADO ENTRE VARIOS PCs
:: Para que este computador use o mesmo banco de outro, tire o REM da
:: linha abaixo e troque pelo caminho da pasta de rede:
::
:: set VOASUL_DADOS=\\SERVIDOR\voasul\dados
::
:: Deixando como esta, cada PC guarda seus dados na pasta local
:: "dados", dentro desta mesma pasta.
:: ------------------------------------------------------------------

:: Porta do servidor local. Se estiver ocupada, o sistema usa a seguinte.
set VOASUL_PORTA=8770

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)

if not defined PY (
  color 0C
  echo.
  echo  Python nao encontrado. Rode o arquivo instalar.bat primeiro.
  echo.
  pause
  exit /b 1
)

%PY% -m voasul_erp
if not %errorlevel%==0 (
  color 0C
  echo.
  echo  O sistema encerrou com erro. A mensagem acima explica o motivo.
  echo.
  pause
)
