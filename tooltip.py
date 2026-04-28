import tkinter as tk

class Tooltip:
    def __init__(self, widget, text, delay=300):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip = None
        self.after_id = None

        widget.bind("<Enter>", self.schedule)
        widget.bind("<Leave>", self.hide)

    def schedule(self, event=None):
        self.after_id = self.widget.after(self.delay, self.show)

    def show(self):
        if self.tip is not None:
            return

        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 10
        y = self.widget.winfo_rooty()

        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tip, text=self.text,
            background="lightgrey", fg="black",
            relief="solid", borderwidth=1,
            font=("Arial", 10)
        )

        label.pack(ipadx=5, ipady=3)

    def hide(self, event=None):
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

        if self.tip:
            self.tip.destroy()
            self.tip = None
