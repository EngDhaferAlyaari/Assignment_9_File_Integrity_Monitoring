# Assignment 9 - File Integrity Monitoring (FIM)
**Student:** Eng. Dhafer Alyaari  
**Language:** Python

## English
This program watches a file for changes using **SHA-256**. At the first run, it saves the original hash (baseline). It checks the file every **3 seconds**. If the content changes, it displays a **CRITICAL ALERT** with the old and new hashes. Alerts are also saved in `.fim_baselines/alerts.log`.

**How to run:**
```bash
python fim_monitor.py sample_monitored.txt
```
Edit any character in `sample_monitored.txt` while the program is running. The next check (within approximately 3 seconds) will report a change. Press **Ctrl+C** to stop.

**Other commands:**
```bash
python demo_integrity.py
python -m unittest -v test_fim_monitor.py
python fim_monitor.py sample_monitored.txt --once
python fim_monitor.py sample_monitored.txt --reset-baseline --once
```
The last command approves a new reference hash, so use it only when you trust the new file content. The baseline is **not** updated automatically after an alert.

## بالعربية
يراقب هذا البرنامج سلامة ملف باستخدام بصمة **SHA-256**. عند أول تشغيل يحفظ البصمة الأصلية، ثم يفحص الملف **كل 3 ثوانٍ**. إذا تغير محتوى الملف يعرض تنبيهًا حرجًا مع البصمة القديمة والجديدة، ويحفظ التنبيه في سجل نصي.

**طريقة التشغيل:**
```bash
python fim_monitor.py sample_monitored.txt
```
غيّر حرفًا في الملف أثناء التشغيل. سيظهر التنبيه عند دورة الفحص التالية. لإيقاف البرنامج اضغط **Ctrl+C**.

لتجربة البرنامج والاختبارات:
```bash
python demo_integrity.py
python -m unittest -v test_fim_monitor.py
```
لإعادة اعتماد البصمة بعد تعديل موثوق فقط:
```bash
python fim_monitor.py sample_monitored.txt --reset-baseline --once
```

**Windows:** You can run `Run_Monitor.bat` with Python installed, or `Run_EXE.bat` after GitHub Actions builds `FIM_Monitor.exe`. The EXE is not included until the Windows build succeeds.

**Note:** A local baseline file can itself be edited by someone with access to the machine. This is an educational file integrity checker, not a tamper-proof monitoring service.
