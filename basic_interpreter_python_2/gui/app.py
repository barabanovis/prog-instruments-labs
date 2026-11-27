"""
gui/app.py
==========
Tkinter-интерфейс: редактор, ПОЛИЗ, таблица переменных, вывод,
пошаговое выполнение, точки останова.
"""

import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from frontend.lexer import Lexer, LexerError
from frontend.parser import Parser, ParseError
from backend.interpreter import Interpreter, InterpreterError
from backend.debugger import Debugger
from core.poliz import disassemble

# --- Стиль ---
BG_COLOR = "#1e1e1e"
FG_COLOR = "#d4d4d4"
SEL_BG = "#264f78"
FONT_MAIN = ("Consolas", 11)
FONT_UI = ("Segoe UI", 10)
KW_COLOR = "#569cd6"
STR_COLOR = "#ce9178"
NUM_COLOR = "#b5cea8"
COMMENT_COLOR = "#6a9955"

KW_LIST = ["DIM", "AS", "INTEGER", "REAL", "STRING", "IF", "THEN",
           "ELSE", "ENDIF", "DO", "LOOP", "WHILE", "UNTIL", "FOR",
           "TO", "STEP", "NEXT", "SELECT", "CASE", "ENDSELECT",
           "GOTO", "RETURN", "FUNCTION", "ENDFUNCTION", "PRINT",
           "INPUT", "CALL", "AND", "OR", "NOT"]


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

    # ============================================================
    # 1. СТИЛЬ
    # ============================================================

    def _build_style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR,
                        font=FONT_UI)
        style.configure("TButton", background="#333333", foreground=FG_COLOR,
                        font=FONT_UI, borderwidth=1)
        style.map("TButton", background=[('active', '#444444')])
        style.configure("TNotebook", background=BG_COLOR, borderwidth=0)
        style.configure("TNotebook.Tab", background="#2d2d2d",
                        foreground=FG_COLOR, padding=[10, 5])
        style.map("TNotebook.Tab", background=[('selected', '#1e1e1e')],
                  foreground=[('selected', 'white')])
        style.configure("Treeview", background="#252526", foreground=FG_COLOR,
                        fieldbackground="#252526", font=FONT_MAIN, rowheight=25)
        style.configure("Treeview.Heading", background="#333333",
                        foreground="white", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[('selected', SEL_BG)])

    # ============================================================
    # 2. РАЗМЕТКА
    # ============================================================

    def _build_ui(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # --- левая панель: редактор ---
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)

        tb = ttk.Frame(left_frame)
        tb.pack(fill=tk.X, pady=(0, 5))
        btn_cfg = {"width": 12, "padding": 5}
        ttk.Button(tb, text="📂 Загрузить", command=self.load,
                   **btn_cfg).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="💾 Сохранить", command=self.save,
                   **btn_cfg).pack(side=tk.LEFT, padx=2)
        ttk.Separator(tb, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(tb, text="▶ Запустить", command=self.run,
                   **btn_cfg).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="⏭ Шаг", command=self.step,
                   **btn_cfg).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="🔴 Breakpoint", command=self.toggle_bp,
                   **btn_cfg).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="⏹ Сброс", command=self.reset,
                   **btn_cfg).pack(side=tk.LEFT, padx=2)

        editor_frame = ttk.Frame(left_frame)
        editor_frame.pack(fill=tk.BOTH, expand=True)
        self.editor = tk.Text(editor_frame, wrap='none', font=FONT_MAIN,
                              bg="#1e1e1e", fg=FG_COLOR,
                              insertbackground="white",
                              selectbackground=SEL_BG, undo=True)
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y = ttk.Scrollbar(editor_frame, orient=tk.VERTICAL,
                                 command=self.editor.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.editor.config(yscrollcommand=scroll_y.set)

        # --- правая панель: вкладки ---
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        notebook = ttk.Notebook(right_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        poliz_tab = ttk.Frame(notebook)
        notebook.add(poliz_tab, text="📜 ПОЛИЗ")
        self.poliz_view = tk.Text(poliz_tab, wrap='none',
                                  font=("Consolas", 10), bg="#1e1e1e",
                                  fg="#dcdcdc", state=tk.DISABLED)
        self.poliz_view.pack(fill=tk.BOTH, expand=True)

        vars_tab = ttk.Frame(notebook)
        notebook.add(vars_tab, text="📊 Переменные")
        self.vars_view = ttk.Treeview(vars_tab,
                                      columns=('name', 'type', 'value'),
                                      show='headings')
        self.vars_view.heading('name', text="Имя")
        self.vars_view.heading('type', text="Тип")
        self.vars_view.heading('value', text="Значение")
        self.vars_view.column('name', width=100)
        self.vars_view.column('type', width=100)
        self.vars_view.column('value', width=100)
        self.vars_view.pack(fill=tk.BOTH, expand=True)

        out_tab = ttk.Frame(notebook)
        notebook.add(out_tab, text="📤 Вывод")
        self.out = tk.Text(out_tab, wrap='word', font=FONT_MAIN,
                           bg="#1e1e1e", fg="#dcdcdc", state=tk.DISABLED)
        self.out.pack(fill=tk.BOTH, expand=True)

        self.status = tk.StringVar(value="Готов")
        status_bar = tk.Label(self, textvariable=self.status, bg="#007acc",
                              fg="white", font=("Segoe UI", 9), anchor="w",
                              padx=10)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    # ============================================================
    # 3. ПОДСВЕТКА СИНТАКСИСА
    # ============================================================

    def _setup_tags(self):
        self.editor.tag_configure("kw", foreground=KW_COLOR,
                                  font=(FONT_MAIN[0], FONT_MAIN[1], "bold"))
        self.editor.tag_configure("str", foreground=STR_COLOR)
        self.editor.tag_configure("num", foreground=NUM_COLOR)
        self.editor.tag_configure("comment", foreground=COMMENT_COLOR)
        self.editor.tag_configure("current_line", background="#2a2d2e")
        self.editor.bind("<KeyRelease>", self._highlight_syntax)

    def _highlight_syntax(self, event=None):
        for tag in ("kw", "str", "num", "comment"):
            self.editor.tag_remove(tag, "1.0", tk.END)

        src = self.editor.get("1.0", tk.END)
        for i, line in enumerate(src.split('\n')):
            line_num = i + 1
            if "'" in line:
                start = f"{line_num}.{line.index(chr(39))}"
                self.editor.tag_add("comment", start, f"{line_num}.end")

            # строки
            in_str, start_str = False, None
            for j, ch in enumerate(line):
                if ch == '"':
                    if in_str:
                        self.editor.tag_add(
                            "str", f"{line_num}.{start_str}", f"{line_num}.{j+1}")
                        in_str = False
                    else:
                        in_str, start_str = True, j

            # ключевые слова
            for match in re.finditer(r'\b[A-Za-z_][A-Za-z0-9_]*\b', line):
                if match.group().upper() in KW_LIST:
                    self.editor.tag_add(
                        "kw", f"{line_num}.{match.start()}",
                        f"{line_num}.{match.end()}")
            # числа
            for match in re.finditer(r'\b\d+(\.\d+)?\b', line):
                self.editor.tag_add(
                    "num", f"{line_num}.{match.start()}",
                    f"{line_num}.{match.end()}")

    def _highlight_current_line(self, line_num):
        self.editor.tag_remove("current_line", "1.0", tk.END)
        if line_num:
            start, end = f"{line_num}.0", f"{line_num}.end"
            self.editor.tag_add("current_line", start, end)
            self.editor.see(start)

    # ============================================================
    # 4. ФАЙЛЫ
    # ============================================================

    def load(self):
        p = filedialog.askopenfilename(
            filetypes=[("BASIC", "*.bas"), ("All", "*.*")])
        if p:
            self.editor.delete('1.0', tk.END)
            with open(p, encoding='utf-8') as f:
                self.editor.insert('1.0', f.read())
            self._highlight_syntax()

    def save(self):
        p = filedialog.asksaveasfilename(defaultextension=".bas")
        if p:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(self.editor.get('1.0', tk.END))

    # ============================================================
    # 5. ВЫПОЛНЕНИЕ
    # ============================================================

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
        for view in (self.poliz_view, self.out):
            view.config(state=tk.NORMAL)
            view.delete('1.0', tk.END)
            view.config(state=tk.DISABLED)
        self.vars_view.delete(*self.vars_view.get_children())
        self.status.set("Сброс")

    # ============================================================
    # 6. ОБНОВЛЕНИЕ ПАНЕЛЕЙ
    # ============================================================

    def _refresh(self):
        if self.interp is None:
            return
        self.poliz_view.config(state=tk.NORMAL)
        self.poliz_view.delete('1.0', tk.END)
        self.poliz_view.insert('1.0', disassemble(self.interp.poliz,
                                                  self.interp.pc))
        self.poliz_view.config(state=tk.DISABLED)

        self.vars_view.delete(*self.vars_view.get_children())
        for _, chain in self.interp.symtab.dump():
            for s in chain:
                val = s.value if s.value is not None else "—"
                self.vars_view.insert('', tk.END,
                                      values=(s.name, s.vtype.value, val))

        self.out.config(state=tk.NORMAL)
        self.out.delete('1.0', tk.END)
        self.out.insert('1.0', '\n'.join(self.interp.output))
        self.out.config(state=tk.DISABLED)

        bps = self.dbg.breakpoints if self.dbg else set()
        self.status.set(f"PC: {self.interp.pc:03d} | "
                        f"Стек: {self.interp.stack} | "
                        f"Точки останова: {bps}")
