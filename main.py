import tkinter as tk
from tkinter import ttk
import random
import platform
import matplotlib
matplotlib.use("TkAgg")
import simulator as sim
from simulator import Simulator

class App:
    def __init__(self, root):

        # Definicja zmiennych globalnych
        self.form = 0
        self.shape_options = {
            "rampa": "ramp",
            "skończony prostokąt": "finiteSquare",
            "sinusoidalny": "sineWave",
            "trójkątny": "triangleWave",
        }
        self.nonzero = set()
        self.positive = set()
        self.incorrect_param = set()

        self.root = root
        root.title("Symulator odpowiedzi układu z regulatorem PID")

        self.left_frame = tk.Frame(root, width=300, padx=10, pady=10)
        self.right_frame = tk.Frame(root, padx=10, pady=10)

        self.left_frame.pack(side="left", fill="y")
        self.right_frame.pack(side="right", fill="both", expand=True)

        # --- LEWA STRONA ---
        tk.Label(self.left_frame, text="Panel sterowania", font=("Arial", 14)).pack(pady=5)

        # Pokazana transmitancja
        tk.Label(self.left_frame, text="G₀(s) = (a₁·s + a₀) / (b₂·s² + b₁·s + b₀)", font=("Arial", 14)).pack()

        # Do podania parametry transmitancji
        self.create_parameter_inputs(self.left_frame)

        # Przyciski
        tk.Button(self.left_frame, text="Forma klasyczna", command=lambda: self.switchForm(0)).pack(fill="x", pady=5)
        tk.Button(self.left_frame, text="Forma czasowa", command=lambda: self.switchForm(1)).pack(fill="x", pady=5)

        # Do podania parametry PID
        self.create_pid_inputs(self.left_frame)

        # Lista rozwijana
        tk.Label(self.left_frame, text="Sygnał wejściowy:").pack(anchor="w")
        self.combo = ttk.Combobox(
            self.left_frame,
            values=list(self.shape_options.keys()),
            state="readonly")

        self.combo.current(0)
        self.combo.pack(fill="x", pady=5)
        self.combo.bind("<<ComboboxSelected>>", self.on_shape_selected)

        self.shape_frame = tk.Frame(self.left_frame)
        self.shape_frame.pack(fill="x", pady=10)

        self.build_ramp_inputs()

        self.sim_button = tk.Button(self.left_frame, text="Symulacja", command=self.run_simulation)
        self.sim_button.pack(fill="x", pady=20)

        self.stop_button = tk.Button(self.left_frame, text="STOP", command=self.stop_simulation)
        self.stop_button.pack(fill="x", pady=5)

        # --- PRAWA STRONA ---
        # Wykres
        self.fig = None
        self.ax = None
        self.canvas = None

        self.x_data = []
        self.y_data = []

        # Animacja wykresu i wykres
        self.root.after(1000, self.start_plot)

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.root.quit()
        self.root.destroy()

    def start_plot(self):
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import matplotlib.animation as animation

        self.fig, self.ax = plt.subplots(figsize=(5, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.ax.set_title("Wykres odpowiedzi układu z regulatorem PID")
        self.ax.set_xlabel("Czas")
        self.ax.set_ylabel("Amplituda")
        self.ax.grid(True, linestyle="--", alpha=0.5)


        # Pole tekstowe (logi)
        self.log_box = tk.Text(self.right_frame, height=10)
        self.log_box.pack(fill="x", pady=10)
        self.log_box.config(state="disabled")

        #self.ani = animation.FuncAnimation(self.fig, self.update_plot, interval=500)
        
    # --- FUNKCJE PRZYCISKÓW ---
    def switchForm(self, form):
        """
        Zmiena formę transmitancji sterownika między klasyczną (0) a czasową (1)
        """
        self.form = (int) (form == 1)
        self.build_pid_row2()
        
    def stop_simulation(self):
        if hasattr(self, "Sim"):
            self.Sim.finished = True
            self.log("Symulacja zatrzymana przez użytkownika.")

    # --- LOGOWANIE ---
    def log(self, text):
        self.log_box.config(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.config(state="disabled")
        self.log_box.see("end")

    def create_parameter_inputs(self, parent):

        # Słownik przechowujący zmienne
        self.params = {
            "a1": tk.DoubleVar(value=1),
            "a0": tk.DoubleVar(value=2),
            "b2": tk.DoubleVar(value=2),
            "b1": tk.DoubleVar(value=1.5),
            "b0": tk.DoubleVar(value=1),
        }

        # Które parametry nie mogą być zerem
        self.nonzero.update({"b2"}) 

        frame = tk.Frame(parent)
        frame.pack(pady=10, fill="x")

        # --- Rząd A ---
        row_a = tk.Frame(frame)
        row_a.pack(fill="x", pady=3)

        tk.Label(row_a, text="a1:", width=4).pack(side="left")
        entry_a1 = tk.Entry(row_a, textvariable=self.params["a1"], width=8)
        entry_a1.pack(side="left", padx=5)

        tk.Label(row_a, text="a0:", width=4).pack(side="left")
        entry_a0 = tk.Entry(row_a, textvariable=self.params["a0"], width=8)
        entry_a0.pack(side="left", padx=5)

        # --- Rząd B ---
        row_b = tk.Frame(frame)
        row_b.pack(fill="x", pady=3)

        tk.Label(row_b, text="b2:", width=4).pack(side="left")
        entry_b2 = tk.Entry(row_b, textvariable=self.params["b2"], width=8)
        entry_b2.pack(side="left", padx=5)

        tk.Label(row_b, text="b1:", width=4).pack(side="left")
        entry_b1 = tk.Entry(row_b, textvariable=self.params["b1"], width=8)
        entry_b1.pack(side="left", padx=5)

        tk.Label(row_b, text="b0:", width=4).pack(side="left")
        entry_b0 = tk.Entry(row_b, textvariable=self.params["b0"], width=8)
        entry_b0.pack(side="left", padx=5)

        # Walidacja dla wszystkich pól
        for name, widget in [
            ("a1", entry_a1),
            ("a0", entry_a0),
            ("b2", entry_b2),
            ("b1", entry_b1),
            ("b0", entry_b0),
        ]:
            widget.bind("<KeyRelease>", lambda e, n=name, w=widget: self.validate_param(n, w))

        self.t_params = [entry_a1, entry_a0, entry_b2, entry_b1, entry_b0]
    
    def build_pid_row2(self):
        # usuń stare pola
        for widget in self.pid_row2.winfo_children():
            widget.destroy()

        if self.form == 0:
            # Forma klasyczna → Ki, Kd
            tk.Label(self.pid_row2, text="Ki:", width=4).pack(side="left")
            self.entry_Ki = tk.Entry(self.pid_row2, textvariable=self.pid_vars["Ki"], width=8)
            self.entry_Ki.pack(side="left", padx=5)

            tk.Label(self.pid_row2, text="Kd:", width=4).pack(side="left")
            self.entry_Kd = tk.Entry(self.pid_row2, textvariable=self.pid_vars["Kd"], width=8)
            self.entry_Kd.pack(side="left", padx=5)

            # walidacja
            self.entry_Ki.bind("<KeyRelease>", lambda e: self.validate_param("Ki", self.entry_Ki))
            self.entry_Kd.bind("<KeyRelease>", lambda e: self.validate_param("Kd", self.entry_Kd))

        else:
            # Forma czasowa → Ti, Td
            tk.Label(self.pid_row2, text="Ti [s]:", width=4).pack(side="left")
            self.entry_Ti = tk.Entry(self.pid_row2, textvariable=self.pid_vars["Ti"], width=8)
            self.entry_Ti.pack(side="left", padx=5)

            tk.Label(self.pid_row2, text="Td [s]:", width=4).pack(side="left")
            self.entry_Td = tk.Entry(self.pid_row2, textvariable=self.pid_vars["Td"], width=8)
            self.entry_Td.pack(side="left", padx=5)

            # walidacja
            self.entry_Ti.bind("<KeyRelease>", lambda e: self.validate_param("Ti", self.entry_Ti))
            self.entry_Td.bind("<KeyRelease>", lambda e: self.validate_param("Td", self.entry_Td))

    def create_pid_inputs(self, parent):

        # PID zmienne
        self.pid_vars = {
            "Kp": tk.DoubleVar(value=2),
            "Tf": tk.DoubleVar(value=0.2),

            "Ki": tk.DoubleVar(value=1),
            "Kd": tk.DoubleVar(value=0.5),

            "Ti": tk.DoubleVar(value=1),
            "Td": tk.DoubleVar(value=0.5),

            "Umax": tk.DoubleVar(value=3),
        }

        self.nonzero.update({"Kp", "Tf", "Ki", "Kd", "Ti", "Td"})
        self.positive.update({"Tf", "Ti", "Td"})

        # Ramka główna
        self.pid_frame = tk.Frame(parent)
        self.pid_frame.pack(pady=10, fill="x")

        # --- Rząd 1: Kp, Tf ---
        row1 = tk.Frame(self.pid_frame)
        row1.pack(fill="x", pady=3)

        tk.Label(row1, text="Kp:", width=4).pack(side="left")
        self.entry_Kp = tk.Entry(row1, textvariable=self.pid_vars["Kp"], width=8)
        self.entry_Kp.pack(side="left", padx=5)

        tk.Label(row1, text="Tf [s]:", width=4).pack(side="left")
        self.entry_Tf = tk.Entry(row1, textvariable=self.pid_vars["Tf"], width=8)
        self.entry_Tf.pack(side="left", padx=5)

        # --- Rząd 2: dynamiczny ---
        self.pid_row2 = tk.Frame(self.pid_frame)
        self.pid_row2.pack(fill="x", pady=3)

        self.build_pid_row2()

        # --- Rząd 3: Saturacja ---
        row3 = tk.Frame(self.pid_frame)
        row3.pack(fill="x", pady=3)

        tk.Label(row3, text="Umax:", width=6).pack(side="left")
        self.entry_Umax = tk.Entry(row3, textvariable=self.pid_vars["Umax"], width=8)
        self.entry_Umax.pack(side="left", padx=5)

        # wymagania walidacyjne
        self.nonzero.add("Umax")
        self.positive.add("Umax")


        # Walidacja dla statycznych pól
        self.entry_Kp.bind("<KeyRelease>", lambda e: self.validate_param("Kp", self.entry_Kp))
        self.entry_Tf.bind("<KeyRelease>", lambda e: self.validate_param("Tf", self.entry_Tf))
        self.entry_Umax.bind("<KeyRelease>", lambda e: self.validate_param("Umax", self.entry_Umax))

    def build_ramp_inputs(self):
        tk.Label(self.shape_frame, text="Parametry rampy:", font=("Arial", 12)).pack(anchor="w")

        # zmienne rampy
        self.ramp_vars = {
            "rise_time": tk.DoubleVar(value=1),
            "amplitude": tk.DoubleVar(value=1),
        }

        # wymagania walidacyjne
        self.positive.update({"rise_time", "amplitude"})  # muszą być > 0
        self.nonzero.update({"rise_time", "amplitude"}) 

        # --- czas narastania ---
        row1 = tk.Frame(self.shape_frame)
        row1.pack(fill="x", pady=3)

        tk.Label(row1, text="Czas narastania [ms]:", width=20).pack(side="left")
        entry_rt = tk.Entry(row1, textvariable=self.ramp_vars["rise_time"], width=10)
        entry_rt.pack(side="left")
        entry_rt.bind("<KeyRelease>", lambda e: self.validate_param("rise_time", entry_rt))

        # --- amplituda ---
        row2 = tk.Frame(self.shape_frame)
        row2.pack(fill="x", pady=3)

        tk.Label(row2, text="Amplituda [V]:", width=20).pack(side="left")
        entry_amp = tk.Entry(row2, textvariable=self.ramp_vars["amplitude"], width=10)
        entry_amp.pack(side="left")
        entry_amp.bind("<KeyRelease>", lambda e: self.validate_param("amplitude", entry_amp))

    def build_finite_square_inputs(self):
        tk.Label(self.shape_frame, text="Parametry sygnału prostokątnego:", font=("Arial", 12)).pack(anchor="w")

        # zmienne rampy
        self.finite_square_vars = {
            "duration": tk.DoubleVar(value=1),
            "amplitude": tk.DoubleVar(value=1),
        }

        # wymagania walidacyjne
        self.positive.update({"duration", "amplitude"})
        self.nonzero.update({"duration", "amplitude"})

        # --- czas trwania ---
        row1 = tk.Frame(self.shape_frame)
        row1.pack(fill="x", pady=3)

        tk.Label(row1, text="Czas trwania [ms]:", width=20).pack(side="left")
        entry_dt = tk.Entry(row1, textvariable=self.finite_square_vars["duration"], width=10)
        entry_dt.pack(side="left")
        entry_dt.bind("<KeyRelease>", lambda e: self.validate_param("duration", entry_dt))

        # --- amplituda ---
        row2 = tk.Frame(self.shape_frame)
        row2.pack(fill="x", pady=3)

        tk.Label(row2, text="Amplituda [V]:", width=20).pack(side="left")
        entry_amp = tk.Entry(row2, textvariable=self.finite_square_vars["amplitude"], width=10)
        entry_amp.pack(side="left")
        entry_amp.bind("<KeyRelease>", lambda e: self.validate_param("amplitude", entry_amp))

    def build_sine_wave_inputs(self):

        tk.Label(self.shape_frame, text="Parametry sygnału harmonicznego:", font=("Arial", 12)).pack(anchor="w")

        # zmienne rampy
        self.sine_wave_vars = {
            "frequency": tk.DoubleVar(value=1),
            "amplitude": tk.DoubleVar(value=1),
            "delay": tk.DoubleVar(value=0)
        }

        # wymagania walidacyjne
        self.positive.update({"frequency", "amplitude"})
        self.nonzero.update({"frequency", "amplitude"})

        # --- czas trwania ---
        row1 = tk.Frame(self.shape_frame)
        row1.pack(fill="x", pady=3)

        tk.Label(row1, text="Częstotliwość [Hz]:", width=20).pack(side="left")
        entry_f = tk.Entry(row1, textvariable=self.sine_wave_vars["frequency"], width=10)
        entry_f.pack(side="left")
        entry_f.bind("<KeyRelease>", lambda e: self.validate_param("frequency", entry_f))

        # --- amplituda ---
        row2 = tk.Frame(self.shape_frame)
        row2.pack(fill="x", pady=3)

        tk.Label(row2, text="Amplituda [V]:", width=20).pack(side="left")
        entry_amp = tk.Entry(row2, textvariable=self.sine_wave_vars["amplitude"], width=10)
        entry_amp.pack(side="left")
        entry_amp.bind("<KeyRelease>", lambda e: self.validate_param("amplitude", entry_amp))

        # --- przesunięcie fazy ---
        row2 = tk.Frame(self.shape_frame)
        row2.pack(fill="x", pady=3)

        tk.Label(row2, text="Przesunięcie fazy [st]:", width=20).pack(side="left")
        entry_dl = tk.Entry(row2, textvariable=self.sine_wave_vars["delay"], width=10)
        entry_dl.pack(side="left")
        entry_dl.bind("<KeyRelease>", lambda e: self.validate_param("delay", entry_dl))

        # zmienne rampy
        self.sine_wave_vars = {
            "frequency": tk.DoubleVar(value=1),
            "amplitude": tk.DoubleVar(value=1),
            "delay": tk.DoubleVar(value=0)
        }

    def build_triangle_wave_inputs(self):

        tk.Label(self.shape_frame, text="Parametry sygnału trójkątnego:", font=("Arial", 12)).pack(anchor="w")

        # zmienne rampy
        self.triangle_wave_vars = {
            "raise_time": tk.DoubleVar(value=1),
            "fall_time": tk.DoubleVar(value=0),
            "amplitude": tk.DoubleVar(value=1)
        }

        # wymagania walidacyjne
        self.positive.update({"raise_time", "fall_time", "amplitude"})
        self.nonzero.update({"raise_time", "amplitude"})

        # --- czas narastania ---
        row1 = tk.Frame(self.shape_frame)
        row1.pack(fill="x", pady=3)

        tk.Label(row1, text="Czas narastania [ms]:", width=20).pack(side="left")
        entry_rt = tk.Entry(row1, textvariable=self.triangle_wave_vars["raise_time"], width=10)
        entry_rt.pack(side="left")
        entry_rt.bind("<KeyRelease>", lambda e: self.validate_param("raise_time", entry_rt))

        # --- czas opadania ---
        row2 = tk.Frame(self.shape_frame)
        row2.pack(fill="x", pady=3)

        tk.Label(row2, text="Czas opadania [ms]:", width=20).pack(side="left")
        entry_ft = tk.Entry(row2, textvariable=self.triangle_wave_vars["fall_time"], width=10)
        entry_ft.pack(side="left")
        entry_ft.bind("<KeyRelease>", lambda e: self.validate_param("fall_time", entry_ft))

        # --- amplituda ---
        row2 = tk.Frame(self.shape_frame)
        row2.pack(fill="x", pady=3)

        tk.Label(row2, text="Amplituda [V]:", width=20).pack(side="left")
        entry_amp = tk.Entry(row2, textvariable=self.triangle_wave_vars["amplitude"], width=10)
        entry_amp.pack(side="left")
        entry_amp.bind("<KeyRelease>", lambda e: self.validate_param("amplitude", entry_amp))

    def on_shape_selected(self, event):
        self.combo.selection_clear()

        label = self.combo.get()
        internal_value = self.shape_options[label]

        # wyczyść ramkę na pola
        for widget in self.shape_frame.winfo_children():
            widget.destroy()

        match internal_value:
            #case "impulse":
            case "ramp":
                self.build_ramp_inputs()
            case "finiteSquare":
                self.build_finite_square_inputs()
            case "sineWave":
                self.build_sine_wave_inputs()
            case "triangleWave":
                self.build_triangle_wave_inputs()

    def tick(self):
        if self.Sim.run():
            self.root.after(20, self.tick)   # kontynuuj

    def run_simulation(self):

        selected = self.shape_options[self.combo.get()]

        match selected:

            case "ramp":
                rt = self.ramp_vars["rise_time"].get()
                amp = self.ramp_vars["amplitude"].get()
                self.current_shape = sim.Ramp(rt, amp)

            case "finiteSquare":
                d = self.finite_square_vars["duration"].get()
                amp = self.finite_square_vars["amplitude"].get()
                self.current_shape = sim.FiniteSquare(d, amp)

            case "sineWave":
                fr = self.sine_wave_vars["frequency"].get()
                amp = self.sine_wave_vars["amplitude"].get()
                dl = self.sine_wave_vars["delay"].get()
                self.current_shape = sim.SineWave(fr, amp, dl)

            case "triangleWave":
                rt = self.triangle_wave_vars["raise_time"].get()
                ft = self.triangle_wave_vars["fall_time"].get()
                amp = self.triangle_wave_vars["amplitude"].get()
                self.current_shape = sim.TriangleWave(rt, ft, amp)
            
        a1 = self.params["a1"].get()
        a0 = self.params["a0"].get()
        b2 = self.params["b2"].get()
        b1 = self.params["b1"].get()
        b0 = self.params["b0"].get()

        Kp = self.pid_vars["Kp"].get()
        Tf = self.pid_vars["Tf"].get()

        t_min = Tf / 20

        if self.form:
            Ti = self.pid_vars["Ti"].get()
            Td = self.pid_vars["Td"].get()
            B  = Kp * Td
            A  = Kp / Ti
            t_min = min((Ti / 20), (Td / 20), t_min)
        else:
            Ki = self.pid_vars["Ki"].get()
            Kd = self.pid_vars["Kd"].get()
            Ti = Kp / Ki
            Td = Kd / Kp
            B = Kd
            A = Ki
            t_min = min((Ti / 20), (Td / 20), t_min)

        Umax = self.pid_vars["Umax"].get()

        params = [a1, a0, b2, b1, b0, Kp, Tf, B, A, Umax]

        self.Sim = Simulator(self.current_shape, t_min, self.ax, self.form, params)
        self.tick()
        #self.canvas.draw()

    def update_sim_button_state(self):
        if len(self.incorrect_param) > 0:
            self.sim_button.config(state="disabled")
        else:
            self.sim_button.config(state="normal")

    def validate_param(self, name, widget):
        text = widget.get()

        # puste pole
        if text.strip() == "":
            widget.config(bg="#ff1919")
            self.incorrect_param.add(name)
            self.update_sim_button_state()
            return

        try:
            value = float(text)
        except ValueError:
            widget.config(bg="#ff1919")
            self.incorrect_param.add(name)
            self.update_sim_button_state()
            return

        # reguły walidacji
        if name in self.nonzero and value == 0:
            widget.config(bg="#ff1919")
            self.incorrect_param.add(name)

        elif name in self.positive and value < 0:
            widget.config(bg="#ff1919")
            self.incorrect_param.add(name)

        else:
            widget.config(bg="#009919")
            if name in self.incorrect_param:
                self.incorrect_param.remove(name)

        self.update_sim_button_state()

# --- START PROGRAMU ---
root = tk.Tk()

# Wieloplatformowa maksymalizacja okna
system_operacyjny = platform.system()
if system_operacyjny == "Linux":
    root.attributes("-zoomed", True)
elif system_operacyjny == "Windows":
    root.state("zoomed")
elif system_operacyjny == "Darwin":  # macOS
    szerokosc = root.winfo_screenwidth()
    wysokosc = root.winfo_screenheight()
    root.geometry(f"{szerokosc}x{wysokosc}+0+0")

app = App(root)
root.mainloop()
