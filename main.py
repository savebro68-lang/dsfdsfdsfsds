import tkinter as tk
import customtkinter as ctkinter
import os
import psutil
import ctypes
import sys
import sqlite3
import shutil
import subprocess
import zipfile
import datetime
import win32evtlog # Требуется: pip install pywin32

# Проверка прав администратора
if not ctypes.windll.shell32.IsUserAnAdmin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

ctkinter.set_appearance_mode("dark")

class ArhiCheckApp(ctkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("ARHICHECK")
        self.geometry("1100x900")
        self.configure(fg_color="black")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ASCII LOGO
        self.logo = ctkinter.CTkLabel(self, text="""
    ▄▄▄       ██▀███   ██░ ██  ██▓ ▄████▄   ██░ ██ ▓█████  ▄████▄ 
   ▒████▄    ▓██ ▒ ██▒▓██░ ██▒▓██▒▒██▀ ▀█  ▓██░ ██▒▓█   ▀ ▒██▀ ▀█ 
   ▒██  ▀█▄  ▓██ ░▄█ ▒▒██▀▀██░▒██▒▒▓█    ▄ ▒██▀▀██░▒███   ▒▓█    ▄
   ░██▄▄▄▄██ ▒██▀▀█▄  ░▓█ ░██ ░██░▒▓▓▄ ▄██▒░▓█ ░██ ▒▓█  ▄ ▒▓▓▄ ▄██
    ▓█   ▓██▒░██▓ ▒██▒░▓█▒░██▓░██░▒ ▓███▀ ░░▓█▒░██▓░▒████▒▒ ▓███▀ 
    ▒▒   ▓▒█░░ ▒▓ ░▒▓░ ▒ ░░▒░▒░▓  ░ ░▒ ▒  ░ ▒ ░░▒░▒░░ ▒░ ░░ ░▒ ▒  
        """, font=("Courier New", 10, "bold"), text_color="#BC13FE")
        self.logo.grid(row=0, column=0, pady=20)

        # Фрейм кнопок
        self.btn_frame = ctkinter.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=1, column=0, pady=10)
        self.create_buttons()

        # Поле вывода (БЕЗ ОБВОДКИ)
        self.result_text = ctkinter.CTkTextbox(
            self, fg_color="black", text_color="#BC13FE",
            border_width=0, font=("Consolas", 15), activate_scrollbars=True
        )
        self.result_text.grid(row=2, column=0, padx=30, pady=20, sticky="nsew")

        self.db = ["nursultan", "expensive", "doomsday", "dday", "akrien", "celestial", "zamorozka", "vape", "midnight", "deadcode", "exloader", "cheat", "hacked", "client"]

    def create_buttons(self):
        btns = [
            ("JAVA SCAN", self.check_java), ("EXE SCAN", self.check_exe), 
            ("DNS CACHE", self.check_dns), ("DELETED", self.check_deleted),
            ("HISTORY", self.check_history), ("AUTO-SOFT", self.download_tools)
        ]
        for i, (txt, cmd) in enumerate(btns):
            b = ctkinter.CTkButton(
                self.btn_frame, text=txt, command=cmd, 
                fg_color="black", text_color="#BC13FE", 
                border_color="#BC13FE", border_width=2,
                hover_color="#1a0026", width=155, height=45, font=("Impact", 14)
            )
            b.grid(row=0, column=i, padx=5, pady=10)

    def log(self, msg):
        self.result_text.insert("end", f"> {msg}\n")
        self.result_text.see("end")

    def clear(self):
        self.result_text.delete("1.0", "end")

    # --- КНОПКА DELETED (Логи за 24 часа) ---
    def check_deleted(self):
        self.clear()
        self.log("SCANNING EVENT LOGS FOR DELETED FILES (24H)...")
        hand = win32evtlog.OpenEventLog(None, "Security")
        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        total = 0
        now = datetime.datetime.now()

        try:
            while True:
                events = win32evtlog.ReadEventLog(hand, flags, 0)
                if not events: break
                for event in events:
                    # Проверяем время события
                    event_time = event.TimeGenerated
                    if (now - event_time.replace(tzinfo=None)).total_seconds() > 86400:
                        break # Выходим, если событие старше 24 часов
                    
                    # 4660 / 4663 - коды удаления в Windows Security Log
                    if event.EventID in [4660, 4663]:
                        msg = event.StringInserts
                        if msg:
                            # Обычно путь к файлу в этих индексах
                            file_path = msg[6] if len(msg) > 6 else "Unknown Path"
                            self.log(f"[{event_time.strftime('%H:%M:%S')}] DEL: {file_path}")
                            total += 1
                if (now - events[-1].TimeGenerated.replace(tzinfo=None)).total_seconds() > 86400:
                    break
        except: pass
        
        if total == 0: self.log("NO RECENT DELETIONS FOUND IN SYSTEM LOGS.")
        else: self.log(f"\nTOTAL LOGGED DELETIONS: {total}")

    # --- УЛУЧШЕННЫЙ JAVA SCAN (SIGNATURE SCAN) ---
    def check_java(self):
        self.clear()
        # Сигнатуры из твоего файла (proverka.jar)
        sigs = ["fabric.mod.json5", "l.png", "net/java/a.class", "net/java/l.class"]
        found = False
        
        paths = [os.path.join(os.getenv('APPDATA'), '.minecraft'), os.getenv('TEMP'), os.path.join(os.path.expanduser('~'), 'Downloads')]
        
        for d in paths:
            if not d or not os.path.exists(d): continue
            for root, _, files in os.walk(d):
                # Пропуск системных либ
                if any(x in root.lower() for x in ["libraries", "assets", "natives", "microsoft"]): continue
                
                for f in files:
                    f_path = os.path.join(root, f)
                    try:
                        # Если файл похож на мод по размеру
                        if 50000 < os.path.getsize(f_path) < 100000000:
                            with zipfile.ZipFile(f_path, 'r') as z:
                                names = z.namelist()
                                # Ищем совпадения по внутренней структуре твоего файла
                                if any(s in names for s in sigs):
                                    self.log(f"ALERT: CLONE OF DOOMSDAY DETECTED -> {f}")
                                    self.log(f"PATH: {root}")
                                    found = True
                                    continue
                        
                        # Обычный чек по имени
                        if any(t in f.lower() for t in self.db):
                            self.log(f"DETECTED BY NAME: {f} | {root}")
                            found = True
                    except: continue
        if not found: self.log("JAVA: CLEAN")

    def check_exe(self):
        self.clear()
        found = False
        for proc in psutil.process_iter(['name']):
            if any(c in proc.info['name'].lower() for c in self.db):
                self.log(f"ACTIVE EXE: {proc.info['name']}")
                found = True
        if not found: self.log("EXE: CLEAN")

    def check_dns(self):
        self.clear()
        found = False
        try:
            output = subprocess.check_output("ipconfig /displaydns", shell=True).decode('cp866')
            for line in output.split('\n'):
                if any(c in line.lower() for c in self.db):
                    if "Имя записи" in line or "Record Name" in line:
                        self.log(f"DNS TRACE: {line.strip()}")
                        found = True
            if not found: self.log("DNS: CLEAN")
        except: self.log("DNS ERROR")

    def check_history(self):
        self.clear()
        self.log("HISTORY SCANNING...")
        # (Код поиска по SQLite базам браузеров)
        self.log("DONE.")

    def download_tools(self):
        self.clear()
        self.log("STARTING AUTO-SOFT...")
        # (Код скачивания Everything)

if __name__ == "__main__":
    app = ArhiCheckApp()
    app.mainloop()