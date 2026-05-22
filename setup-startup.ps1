$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\论文搜搜.lnk")
$Shortcut.TargetPath = "C:\Users\lenovo\Desktop\美妙的搜论文网站\start-silent.vbs"
$Shortcut.WorkingDirectory = "C:\Users\lenovo\Desktop\美妙的搜论文网站"
$Shortcut.Description = "论文搜搜网站自动启动"
$Shortcut.Save()
Write-Host "已创建启动快捷方式: $env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\论文搜搜.lnk"
