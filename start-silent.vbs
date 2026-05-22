Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
backendDir = scriptDir & "\backend"

' Try conda env p first, then fall back to system python
pythonPath = "python"
userProfile = WshShell.ExpandEnvironmentStrings("%USERPROFILE%")
condaPython = userProfile & "\.conda\envs\p\python.exe"
If fso.FileExists(condaPython) Then
    pythonPath = condaPython
End If

WshShell.Run "cmd /c ""cd /d """ & backendDir & """ && """ & pythonPath & """ run.py""", 0, False
