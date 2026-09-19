from __future__ import annotations

import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from krishna_console import ensure_core, _request, STARTUP_ERRORS


class KrishnaDesktop(tk.Tk):
    BG = "#0b1020"
    PANEL = "#111827"
    PANEL2 = "#172033"
    TEXT = "#e5eefb"
    MUTED = "#93a4bd"
    ACCENT = "#5ee7ff"
    USER = "#1f6feb"
    ASSISTANT = "#182235"

    def __init__(self):
        super().__init__()
        self.title("KRISHNA")
        self.geometry("1220x790")
        self.minsize(900, 620)
        self.configure(bg=self.BG)

        self.active_project = "general"
        self.active_chat = None
        self.projects = []
        self.chats = []

        self._build_style()
        self._build_ui()
        self.after(100, self._boot)

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=self.BG)
        style.configure("Sidebar.TFrame", background=self.PANEL)
        style.configure("TLabel", background=self.BG, foreground=self.TEXT)
        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"), foreground=self.ACCENT)
        style.configure("Muted.TLabel", foreground=self.MUTED)
        style.configure("TButton", padding=7)
        style.configure("Accent.TButton", padding=8, font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True)

        sidebar = ttk.Frame(root, style="Sidebar.TFrame", width=285)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        main = ttk.Frame(root)
        main.pack(side="left", fill="both", expand=True)

        brand = tk.Label(
            sidebar, text="KRISHNA", bg=self.PANEL, fg=self.ACCENT,
            font=("Segoe UI", 18, "bold"), anchor="w",
        )
        brand.pack(fill="x", padx=16, pady=(18, 2))
        tk.Label(
            sidebar, text="Your AI · Your Control", bg=self.PANEL, fg=self.MUTED,
            font=("Segoe UI", 9), anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 15))

        proj_head = tk.Frame(sidebar, bg=self.PANEL)
        proj_head.pack(fill="x", padx=12)
        tk.Label(proj_head, text="PROJECTS", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 8, "bold")).pack(side="left")
        tk.Button(
            proj_head, text="+ Project", command=self.new_project,
            bg=self.PANEL2, fg=self.TEXT, relief="flat", activebackground="#24324a",
        ).pack(side="right")

        self.project_list = tk.Listbox(
            sidebar, height=8, bg=self.PANEL, fg=self.TEXT, selectbackground="#243d60",
            selectforeground="white", highlightthickness=0, relief="flat",
            font=("Segoe UI", 10),
        )
        self.project_list.pack(fill="x", padx=10, pady=(5, 12))
        self.project_list.bind("<<ListboxSelect>>", self._on_project)

        chat_head = tk.Frame(sidebar, bg=self.PANEL)
        chat_head.pack(fill="x", padx=12)
        tk.Label(chat_head, text="CHATS", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 8, "bold")).pack(side="left")
        tk.Button(
            chat_head, text="+ Chat", command=self.new_chat,
            bg=self.PANEL2, fg=self.TEXT, relief="flat", activebackground="#24324a",
        ).pack(side="right")

        self.chat_list = tk.Listbox(
            sidebar, bg=self.PANEL, fg=self.TEXT, selectbackground="#243d60",
            selectforeground="white", highlightthickness=0, relief="flat",
            font=("Segoe UI", 10),
        )
        self.chat_list.pack(fill="both", expand=True, padx=10, pady=(5, 12))
        self.chat_list.bind("<<ListboxSelect>>", self._on_chat)

        bottom_side = tk.Frame(sidebar, bg=self.PANEL)
        bottom_side.pack(fill="x", padx=10, pady=(0, 12))
        tk.Button(
            bottom_side, text="Core Engines", command=self.show_engines,
            bg=self.PANEL2, fg=self.TEXT, relief="flat",
        ).pack(fill="x", pady=2)
        tk.Button(
            bottom_side, text="Status", command=self.show_status,
            bg=self.PANEL2, fg=self.TEXT, relief="flat",
        ).pack(fill="x", pady=2)

        header = tk.Frame(main, bg=self.BG, height=68)
        header.pack(fill="x")
        header.pack_propagate(False)
        self.header_title = tk.Label(
            header, text="General", bg=self.BG, fg=self.TEXT,
            font=("Segoe UI", 14, "bold"), anchor="w",
        )
        self.header_title.pack(side="left", padx=20)

        tools = tk.Frame(header, bg=self.BG)
        tools.pack(side="right", padx=14)
        for text, fn in (
            ("Index", self.index_project),
            ("Inspect UI", self.inspect_ui),
            ("Investigate", self.investigate),
            ("Research GitHub", self.research_github),
        ):
            tk.Button(
                tools, text=text, command=fn, bg=self.PANEL2, fg=self.TEXT,
                relief="flat", padx=10, pady=6, activebackground="#24324a",
            ).pack(side="left", padx=3)

        self.transcript = tk.Text(
            main, wrap="word", bg=self.BG, fg=self.TEXT, insertbackground=self.TEXT,
            relief="flat", borderwidth=0, font=("Segoe UI", 11), padx=20, pady=15,
        )
        self.transcript.pack(fill="both", expand=True)
        self.transcript.configure(state="disabled")
        self.transcript.tag_configure("user_label", foreground="#78a9ff", font=("Segoe UI", 9, "bold"))
        self.transcript.tag_configure("assistant_label", foreground=self.ACCENT, font=("Segoe UI", 9, "bold"))
        self.transcript.tag_configure("tool_label", foreground="#f4c95d", font=("Segoe UI", 9, "bold"))
        self.transcript.tag_configure("body", foreground=self.TEXT, spacing3=12)

        composer = tk.Frame(main, bg=self.BG)
        composer.pack(fill="x", padx=18, pady=(6, 8))
        self.input = tk.Text(
            composer, height=3, wrap="word", bg=self.PANEL2, fg=self.TEXT,
            insertbackground=self.TEXT, relief="flat", font=("Segoe UI", 11),
            padx=12, pady=10,
        )
        self.input.pack(side="left", fill="x", expand=True)
        self.input.bind("<Control-Return>", lambda e: self.send_message())
        self.input.bind("<Shift-Return>", lambda e: None)
        tk.Button(
            composer, text="Send", command=self.send_message, bg="#136f8a",
            fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
            padx=18, pady=12,
        ).pack(side="left", padx=(8, 0), fill="y")

        self.status = tk.Label(
            main, text="Starting KRISHNA Core…", bg=self.BG, fg=self.MUTED,
            font=("Segoe UI", 8), anchor="w",
        )
        self.status.pack(fill="x", padx=20, pady=(0, 9))

    def _set_status(self, text):
        self.status.config(text=text)

    def _append(self, role, text):
        self.transcript.configure(state="normal")
        label_tag = "tool_label" if role == "TOOL" else ("user_label" if role == "YOU" else "assistant_label")
        self.transcript.insert("end", role + "\n", label_tag)
        self.transcript.insert("end", str(text).strip() + "\n\n", "body")
        self.transcript.see("end")
        self.transcript.configure(state="disabled")

    def _run(self, fn, callback=None, label="Working…"):
        self._set_status(label)
        def worker():
            try:
                result = fn()
                error = None
            except Exception as exc:
                result = None
                error = f"{type(exc).__name__}: {exc}"
            self.after(0, lambda: self._finish_run(result, error, callback))
        threading.Thread(target=worker, daemon=True).start()

    def _finish_run(self, result, error, callback):
        self._set_status("Ready")
        if error:
            messagebox.showerror("KRISHNA", error)
            return
        if callback:
            callback(result)

    def _boot(self):
        def start():
            ok = ensure_core()
            return {"ok": ok, "errors": list(STARTUP_ERRORS)}
        def ready(result):
            if not result["ok"]:
                detail = "\n".join(result["errors"][-5:]) or "Unknown startup error"
                messagebox.showerror("KRISHNA Core", "Core could not start:\n\n" + detail)
                self._set_status("Core offline")
                return
            self._set_status("Core online")
            self.refresh_projects()
        self._run(start, ready, "Starting bundled KRISHNA Core…")

    def refresh_projects(self):
        result = _request("/api/projects")
        rows = result.get("projects") or []
        self.projects = [{"name": "general", "root": ""}] + [r for r in rows if r.get("name") != "general"]
        self.project_list.delete(0, "end")
        for item in self.projects:
            self.project_list.insert("end", item.get("name", ""))
        index = next((i for i, x in enumerate(self.projects) if x.get("name") == self.active_project), 0)
        self.project_list.selection_set(index)
        self.project_list.activate(index)
        self.load_chats(self.projects[index]["name"])

    def load_chats(self, project):
        self.active_project = project
        result = _request("/api/chats?project=" + project)
        self.chats = result.get("chats") or []
        if not self.chats:
            created = _request("/api/chats/create", {"project": project, "title": "General"})
            if created.get("chat_id"):
                self.chats = [created]
        self.chat_list.delete(0, "end")
        for item in self.chats:
            self.chat_list.insert("end", item.get("title") or "New chat")
        if self.chats:
            self.chat_list.selection_set(0)
            self.chat_list.activate(0)
            self.open_chat(self.chats[0])
        else:
            self.active_chat = None
            self.header_title.config(text=project)
            self._render_history([])

    def open_chat(self, chat):
        self.active_chat = chat.get("chat_id")
        self.header_title.config(text=f"{self.active_project}  ·  {chat.get('title', 'Chat')}")
        history = _request("/api/chat/history?chat_id=" + self.active_chat)
        self._render_history(history.get("messages") or [])

    def _render_history(self, messages):
        self.transcript.configure(state="normal")
        self.transcript.delete("1.0", "end")
        self.transcript.configure(state="disabled")
        for item in messages:
            role = "YOU" if item.get("role") == "user" else "KRISHNA"
            self._append(role, item.get("content", ""))

    def _on_project(self, _event=None):
        sel = self.project_list.curselection()
        if not sel:
            return
        self.load_chats(self.projects[sel[0]]["name"])

    def _on_chat(self, _event=None):
        sel = self.chat_list.curselection()
        if not sel:
            return
        self.open_chat(self.chats[sel[0]])

    def new_project(self):
        name = simpledialog.askstring("New Project", "Project name:", parent=self)
        if not name:
            return
        root = filedialog.askdirectory(title="Choose project folder")
        if not root:
            return
        result = _request("/api/projects/register", {
            "name": name.strip(),
            "root": root,
            "privacy": "local_only",
            "allowed_actions": [],
            "verification_checks": [],
            "metadata": {"created_from": "KRISHNA.exe desktop"},
        })
        if result.get("error"):
            messagebox.showerror("Project", json.dumps(result, indent=2))
            return
        self.active_project = name.strip()
        _request("/api/chats/create", {"project": self.active_project, "title": "Project start"})
        self.refresh_projects()

    def new_chat(self):
        title = simpledialog.askstring("New Chat", "Chat title:", parent=self) or "New chat"
        result = _request("/api/chats/create", {"project": self.active_project, "title": title})
        if result.get("error"):
            messagebox.showerror("Chat", json.dumps(result, indent=2))
            return
        self.load_chats(self.active_project)

    def send_message(self):
        text = self.input.get("1.0", "end").strip()
        if not text or not self.active_chat:
            return
        self.input.delete("1.0", "end")
        self._append("YOU", text)
        payload = {
            "message": text,
            "project": self.active_project,
            "chat_id": self.active_chat,
            "source": "windows-desktop",
        }
        def done(result):
            if result.get("error"):
                self._append("TOOL", json.dumps(result["error"], ensure_ascii=False))
            else:
                self._append("KRISHNA", result.get("text") or result.get("reply") or json.dumps(result, ensure_ascii=False))
                self.load_chats(self.active_project)
        self._run(lambda: _request("/api/core/chat", payload), done, "KRISHNA is thinking…")

    def _tool_result(self, title, fn):
        def done(result):
            self._append("TOOL", title + "\n" + json.dumps(result, indent=2, ensure_ascii=False))
        self._run(fn, done, title + "…")

    def show_status(self):
        self._tool_result("Core Status", lambda: _request("/api/status"))

    def show_engines(self):
        self._tool_result("KRISHNA Core Engines", lambda: _request("/api/capabilities"))

    def index_project(self):
        if self.active_project == "general":
            messagebox.showinfo("Index", "Create/select a project first.")
            return
        self._tool_result("Repository Index", lambda: _request("/api/projects/index", {"project": self.active_project}))

    def inspect_ui(self):
        url = simpledialog.askstring("Inspect UI", "URL to inspect:", parent=self)
        if not url:
            return
        self._tool_result(
            "Chrome/Chromium Inspection",
            lambda: _request("/api/browser/inspect", {"project": self.active_project, "url": url}, timeout=180),
        )

    def investigate(self):
        problem = simpledialog.askstring("Investigate", "Describe the problem:", parent=self)
        if not problem:
            return
        self._tool_result(
            "Investigation",
            lambda: _request("/api/investigate", {"project": self.active_project, "symptom": problem}, timeout=180),
        )

    def research_github(self):
        query = simpledialog.askstring("Research GitHub", "What should KRISHNA search for?", parent=self)
        if not query:
            return
        self._tool_result(
            "GitHub Research",
            lambda: _request("/api/research/github", {"project": self.active_project, "query": query}, timeout=180),
        )


def main():
    app = KrishnaDesktop()
    app.mainloop()


if __name__ == "__main__":
    main()
