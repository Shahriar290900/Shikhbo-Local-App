; Shikhbo Local — NSIS installer script
; Usage: makensis /DOUTFILE="Shikhbo-installer.exe" /DAPP_DIR="dist\Shikhbo" installer.nsi

!define APP_NAME "Shikhbo Local"
!define APP_VERSION "1.0.0"
!define APP_EXE "Shikhbo.exe"
!define INSTALL_DIR "$PROGRAMFILES64\${APP_NAME}"

Name "${APP_NAME}"
OutFile "${OUTFILE}"
InstallDir "${INSTALL_DIR}"
RequestExecutionLevel admin
Unicode true

Page directory
Page instfiles

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "${APP_DIR}\*.*"
  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\${APP_NAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APP_NAME}"
SectionEnd
