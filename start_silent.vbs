Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\Paulo Roberto\OneDrive\Documentos\Default Project\AI-Market-Analyzer\backend"
WshShell.Run """C:\Users\Paulo Roberto\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"" C:\Users\Paulo Roberto\OneDrive\Documentos\Default Project\AI-Market-Analyzer\backend\server_runner.py", 0, False
