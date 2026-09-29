@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title VOA-SUL ERP - Instalacao
color 0B

echo.
echo  ==========================================================
echo     VOA-SUL ERP  -  Instalacao
echo     Controle de estoque e demandas
echo  ==========================================================
echo.

cd /d "%~dp0"

:: ------------------------------------------------------------------
:: 1. Procura o Python instalado na maquina
:: ------------------------------------------------------------------
set "PY="

where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -c "import sys; sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1
  if !errorlevel!==0 set "PY=py -3"
)

if not defined PY (
  where python >nul 2>&1
  if !errorlevel!==0 (
    python -c "import sys; sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1
    if !errorlevel!==0 set "PY=python"
  )
)

if not defined PY (
  color 0C
  echo  [X] Python 3.9 ou superior nao foi encontrado neste computador.
  echo.
  echo      Baixe em:  https://www.python.org/downloads/
  echo      IMPORTANTE: na primeira tela do instalador do Python, marque
  echo      a caixa "Add Python to PATH" antes de clicar em Install.
  echo.
  echo      Depois de instalar o Python, rode este instalador de novo.
  echo.
  pause
  exit /b 1
)

echo  [OK] Python encontrado.
%PY% --version
echo.

:: ------------------------------------------------------------------
:: 2. Confere que os modulos usados fazem parte da instalacao padrao
::    (o sistema nao usa nenhuma biblioteca externa - nada de pip)
:: ------------------------------------------------------------------
%PY% -c "import sqlite3, wsgiref, hashlib, csv" >nul 2>&1
if not %errorlevel%==0 (
  color 0C
  echo  [X] Esta instalacao do Python esta incompleta ^(falta sqlite3^).
  echo      Reinstale o Python a partir do site oficial.
  echo.
  pause
  exit /b 1
)
echo  [OK] Biblioteca padrao completa. Nenhum download necessario.
echo.

:: ------------------------------------------------------------------
:: 3. Pasta de dados
:: ------------------------------------------------------------------
if not exist "dados" mkdir "dados"
echo  [OK] Pasta de dados: %cd%\dados
echo.

:: ------------------------------------------------------------------
:: 4. Prepara o banco e a carga inicial
:: ------------------------------------------------------------------
echo  Preparando o banco de dados...
%PY% -c "import sys; sys.path.insert(0,'.'); from voasul_erp import db; db.iniciar(); print('  [OK] Banco pronto.')"
if not %errorlevel%==0 (
  color 0C
  echo  [X] Falha ao preparar o banco. Veja a mensagem acima.
  pause
  exit /b 1
)
echo.

:: ------------------------------------------------------------------
:: 5. Atalho na area de trabalho
:: ------------------------------------------------------------------
set "ATALHO=%USERPROFILE%\Desktop\VOA-SUL ERP.lnk"
set "VBS=%TEMP%\voasul_atalho.vbs"
(
  echo Set w = CreateObject^("WScript.Shell"^)
  echo Set s = w.CreateShortcut^("%ATALHO%"^)
  echo s.TargetPath = "%~dp0iniciar.bat"
  echo s.WorkingDirectory = "%~dp0"
  echo s.IconLocation = "%SystemRoot%\System32\shell32.dll, 44"
  echo s.Description = "VOA-SUL ERP - controle de estoque e demandas"
  echo s.Save
) > "%VBS%"
cscript //nologo "%VBS%" >nul 2>&1
del "%VBS%" >nul 2>&1

if exist "%ATALHO%" (
  echo  [OK] Atalho criado na area de trabalho.
) else (
  echo  [!] Nao foi possivel criar o atalho. Use o arquivo iniciar.bat.
)
echo.

echo  ==========================================================
echo     Instalacao concluida.
echo.
echo     Para usar: clique em "VOA-SUL ERP" na area de trabalho
echo                ou no arquivo iniciar.bat desta pasta.
echo.
echo     Primeiro acesso:  usuario  admin
echo                       senha    voasul
echo     Troque a senha em Configuracoes logo no primeiro uso.
echo.
echo     COMPARTILHAR ENTRE VARIOS PCs
echo     Copie esta pasta inteira para o outro computador e rode
echo     este instalador la tambem. Para os dois PCs usarem o
echo     MESMO banco, edite o arquivo iniciar.bat e aponte a
echo     variavel VOASUL_DADOS para uma pasta de rede, assim:
echo        set VOASUL_DADOS=\\SERVIDOR\voasul\dados
echo  ==========================================================
echo.
pause
