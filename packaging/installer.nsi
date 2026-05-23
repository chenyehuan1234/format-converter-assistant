!define APP_NAME "格式转换助手"
!define APP_EXE "FormatConverterAssistant.exe"
!define VERSION "0.1.0"

Name "${APP_NAME}"
OutFile "FormatConverterAssistantSetup-${VERSION}.exe"
InstallDir "$PROGRAMFILES64\FormatConverterAssistant"
RequestExecutionLevel admin

Page directory
Page instfiles

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "..\dist\FormatConverterAssistant\*"
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}.lnk"
  RMDir /r "$INSTDIR"
SectionEnd

