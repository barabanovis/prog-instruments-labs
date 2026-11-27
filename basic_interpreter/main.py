import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from lexer import Lexer, LexerError
from parser import Parser, ParseError
from interpreter import Interpreter, InterpreterError
from debugger import Debugger
from poliz import disassemble

# --- Константы стиля ---
BG_COLOR = "#1e1e1e"
FG_COLOR = "#d4d4d4"
SEL_BG = "#264f78"
FONT_MAIN = ("Consolas", 11)
FONT_UI = ("Segoe UI", 10)

# Цвета подсветки
KW_COLOR = "#569cd6"
STR_COLOR = "#ce9178"
NUM_COLOR = "#b5cea8"
COMMENT_COLOR = "#6a9955"
OP_COLOR = "#d4d4d4"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BASIC Interpreter — вариант 3-2-1-A")
        self.geometry("1300x850")
        self.configure(bg=BG_COLOR)
        
        self.interp = None
        self.dbg = None
        self._build_style()
        self._build_ui()
        self._setup_tags()

    def _build_style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        
        # Настройка цветов для ttk
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR, font=FONT_UI)
        style.configure("TButton", background="#333333", foreground=FG_COLOR, 
                        font=FONT_UI, borderwidth=1)
        style.map("TButton", background=[('active', '#444444')])
        
        style.configure("TNotebook", background=BG_COLOR, borderwidth=0)
        style.configure("TNotebook.Tab", background="#2d2d2d", foreground=FG_COLOR, padding=[10, 5])
        style.map("TNotebook.Tab", background=[('selected', '#1e1e1e')], foreground=[('selected', 'white')])
        
        style.configure("Treeview", background="#252526", foreground=FG_COLOR, 
                        fieldbackground="#252526", font=FONT_MAIN, rowheight=25)
        style.configure("Treeview.Heading", background="#333333", foreground="white", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[('selected', SEL_BG)])

    def _build_ui(self):
        # Главный контейнер
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Горизонтальный PanedWindow
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # ========== ЛЕВАЯ ПАНЕЛЬ (Редактор) ==========
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)

        # Панель инструментов
        tb = ttk.Frame(left_frame)
        tb.pack(fill=tk.X, pady=(0, 5))

        btn_cfg = {"width": 12, "padding": 5}
        ttk.Button(tb, text="📂 Загрузить", command=self.load, **btn_cfg).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="💾 Сохранить", command=self.save, **btn_cfg).pack(side=tk.LEFT, padx=2)
        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(tb, text="▶ Запустить", command=self.run, **btn_cfg).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="⏭ Шаг", command=self.step, **btn_cfg).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="🔴 Breakpoint", command=self.toggle_bp, **btn_cfg).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="⏹ Сброс", command=self.reset, **btn_cfg).pack(side=tk.LEFT, padx=2)

        # Редактор с прокруткой
        editor_frame = ttk.Frame(left_frame)
        editor_frame.pack(fill=tk.BOTH, expand=True)
        
        self.editor = tk.Text(
            editor_frame, wrap='none', font=FONT_MAIN,
            bg="#1e1e1e", fg=FG_COLOR, insertbackground="white",
            selectbackground=SEL_BG, undo=True
        )
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scroll_y = ttk.Scrollbar(editor_frame, orient=tk.VERTICAL, command=self.editor.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.editor.config(yscrollcommand=scroll_y.set)

        # ========== ПРАВАЯ ПАНЕЛЬ (ПОЛИЗ, Переменные, Вывод) ==========
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)

        # Используем Notebook (вкладки) для экономии места
        notebook = ttk.Notebook(right_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Вкладка: ПОЛИЗ
        poliz_tab = ttk.Frame(notebook)
        notebook.add(poliz_tab, text="📜 ПОЛИЗ")
        self.poliz_view = tk.Text(
            poliz_tab, wrap='none', font=("Consolas", 10),
            bg="#1e1e1e", fg="#dcdcdc", state=tk.DISABLED
        )
        self.poliz_view.pack(fill=tk.BOTH, expand=True)

        # Вкладка: Переменные
        vars_tab = ttk.Frame(notebook)
        notebook.add(vars_tab, text="📊 Переменные")
        self.vars_view = ttk.Treeview(
            vars_tab, columns=('name', 'type', 'value'), show='headings'
        )
        self.vars_view.heading('name', text="Имя")
        self.vars_view.heading('type', text="Тип")
        self.vars_view.heading('value', text="Значение")
        self.vars_view.column('name', width=100)
        self.vars_view.column('type', width=100)
        self.vars_view.column('value', width=100)
        self.vars_view.pack(fill=tk.BOTH, expand=True)

        # Вкладка: Вывод
        out_tab = ttk.Frame(notebook)
        notebook.add(out_tab, text="📤 Вывод")
        self.out = tk.Text(
            out_tab, wrap='word', font=FONT_MAIN,
            bg="#1e1e1e", fg="#dcdcdc", state=tk.DISABLED
        )
        self.out.pack(fill=tk.BOTH, expand=True)

        # ========== СТАТУС-БАР ==========
        self.status = tk.StringVar(value="Готов")
        status_bar = tk.Label(
            self, textvariable=self.status,
            bg="#007acc", fg="white", font=("Segoe UI", 9), anchor="w", padx=10
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    # ---------- Подсветка синтаксиса ----------
    def _setup_tags(self):
        """Настройка тегов для подсветки."""
        self.editor.tag_configure("kw", foreground=KW_COLOR, font=(FONT_MAIN[0], FONT_MAIN[1], "bold"))
        self.editor.tag_configure("str", foreground=STR_COLOR)
        self.editor.tag_configure("num", foreground=NUM_COLOR)
        self.editor.tag_configure("comment", foreground=COMMENT_COLOR)
        self.editor.tag_configure("current_line", background="#2a2d2e")
        
        # Привязка событий для обновления подсветки при вводе
        self.editor.bind("<KeyRelease>", self._highlight_syntax)

    def _highlight_syntax(self, event=None):
        """Простая подсветка: удаляем старые теги и ставим новые."""
        for tag in ("kw", "str", "num", "comment"):
            self.editor.tag_remove(tag, "1.0", tk.END)
        
        src = self.editor.get("1.0", tk.END)
        lines = src.split('\n')
        
        kw_list = ["DIM", "AS", "INTEGER", "REAL", "STRING", "IF", "THEN", 
                   "ELSE", "ENDIF", "DO", "LOOP", "WHILE", "UNTIL", "FOR", 
                   "TO", "STEP", "NEXT", "SELECT", "CASE", "ENDSELECT", 
                   "GOTO", "RETURN", "FUNCTION", "ENDFUNCTION", "PRINT", 
                   "INPUT", "CALL", "AND", "OR", "NOT"]
        
        for i, line in enumerate(lines):
            line_num = i + 1
            # Комментарии
            if "'" in line:
                start = f"{line_num}.{line.index(chr(39))}"
                end = f"{line_num}.end"
                self.editor.tag_add("comment", start, end)
            
            # Строки (в кавычках)
            in_str = False
            start_str = None
            for j, ch in enumerate(line):
                if ch == '"':
                    if in_str:
                        self.editor.tag_add("str", f"{line_num}.{start_str}", f"{line_num}.{j+1}")
                        in_str = False
                    else:
                        in_str = True
                        start_str = j
                elif in_str:
                    continue

            # Ключевые слова (упрощенно, без учета строк)
            import re
            for match in re.finditer(r'\b[A-Za-z_][A-Za-z0-9_]*\b', line):
                word = match.group().upper()
                if word in kw_list:
                    start_idx = f"{line_num}.{match.start()}"
                    end_idx = f"{line_num}.{match.end()}"
                    self.editor.tag_add("kw", start_idx, end_idx)
            # Числа
            for match in re.finditer(r'\b\d+(\.\d+)?\b', line):
                start_idx = f"{line_num}.{match.start()}"
                end_idx = f"{line_num}.{match.end()}"
                self.editor.tag_add("num", start_idx, end_idx)

    def _highlight_current_line(self, line_num):
        """Подсветка текущей исполняемой строки."""
        self.editor.tag_remove("current_line", "1.0", tk.END)
        if line_num:
            # Ищем строку в ПОЛИЗе по инструкции
            # Упрощение: просто подсвечиваем строку с номером
            start = f"{line_num}.0"
            end = f"{line_num}.end"
            self.editor.tag_add("current_line", start, end)
            self.editor.see(start)

    # ---------- Логика ----------
    def load(self):
        p = filedialog.askopenfilename(filetypes=[("BASIC", "*.bas"), ("All", "*.*")])
        if p:
            self.editor.delete('1.0', tk.END)
            self.editor.insert('1.0', open(p, encoding='utf-8').read())
            self._highlight_syntax()

    def save(self):
        p = filedialog.asksaveasfilename(defaultextension=".bas")
        if p:
            open(p, 'w', encoding='utf-8').write(self.editor.get('1.0', tk.END))

    def _compile(self):
        src = self.editor.get('1.0', tk.END)
        try:
            tokens = Lexer(src).tokenize()
            poliz, symtab = Parser(tokens).parse()
        except (LexerError, ParseError) as e:
            messagebox.showerror("Ошибка компиляции", str(e))
            return None
        self.interp = Interpreter(poliz, symtab)
        self.dbg = Debugger(self.interp)
        self._refresh()
        return True

    def run(self):
        if not self._compile():
            return
        try:
            self.interp.run()
        except InterpreterError as e:
            messagebox.showerror("Ошибка выполнения", str(e))
        self._refresh()

    def step(self):
        if self.interp is None:
            if not self._compile():
                return
        try:
            self.dbg.step()
        except InterpreterError as e:
            messagebox.showerror("Ошибка выполнения", str(e))
        self._refresh()

    def toggle_bp(self):
        if self.interp is None:
            if not self._compile():
                return
        self.dbg.toggle_breakpoint(self.interp.pc)
        self._refresh()

    def reset(self):
        self.interp = None
        self.dbg = None
        self.poliz_view.config(state=tk.NORMAL)
        self.poliz_view.delete('1.0', tk.END)
        self.poliz_view.config(state=tk.DISABLED)
        self.vars_view.delete(*self.vars_view.get_children())
        self.out.config(state=tk.NORMAL)
        self.out.delete('1.0', tk.END)
        self.out.config(state=tk.DISABLED)
        self.status.set("Сброс")

    def _refresh(self):
        if self.interp is None:
            return
        # Обновление ПОЛИЗа
        self.poliz_view.config(state=tk.NORMAL)
        self.poliz_view.delete('1.0', tk.END)
        dump = disassemble(self.interp.poliz, self.interp.pc)
        self.poliz_view.insert('1.0', dump)
        self.poliz_view.config(state=tk.DISABLED)

        # Обновление переменных
        self.vars_view.delete(*self.vars_view.get_children())
        for _, chain in self.interp.symtab.dump():
            for s in chain:
                val = s.value if s.value is not None else "—"
                self.vars_view.insert('', tk.END, values=(s.name, s.vtype.value, val))

        # Обновление вывода
        self.out.config(state=tk.NORMAL)
        self.out.delete('1.0', tk.END)
        self.out.insert('1.0', '\n'.join(self.interp.output))
        self.out.config(state=tk.DISABLED)

        # Статус
        self.status.set(f"PC: {self.interp.pc:03d} | Стек: {self.interp.stack} | Прерывания: {self.interp.breakpoints}")

        # Подсветка текущей строки (по ПОЛИЗу)
        if self.interp.poliz and self.interp.pc < len(self.interp.poliz):
            # Тут можно привязать инструкцию к строке, если парсер сохраняет line
            pass

if __name__ == '__main__':
    App().mainloop()