import math
import mathFunctions as mf

class FiniteSquare:
    def __init__(self, duration, amplitude):
        self.amplitude = amplitude
        self.duration = duration

    def __str__(self):
        return (
            "Obiekt skończonego, pojedynczego sygnału prostokątnego o parametrach \n"
            "  amplitude - amplituda [V]\n"
            "  duration - czas trwania wartości wysokiej sygnału [ms]\n"
        )
    
    def returnStep(self, t_min):
        return min((self.duration / 20), t_min)

    def getSettlingTime(self):
        return self.duration

    def getValue(self, time):
        if time > self.duration:
            return 0

        return self.amplitude

class Ramp:
    def __init__(self, raise_time, amplitude):
        self.raise_time = raise_time
        self.amplitude = amplitude

    def __str__(self):
        return (
            f"Sygnał rampy o parametrach:\n"
            f"  rise_time - czas narastania [ms]\n"
            f"  amplitude - amplituda [V]\n"
        )
    
    def returnStep(self, t_min):
        return min((self.raise_time / 20), t_min)
    
    def getSettlingTime(self):
        return self.raise_time

    def getValue(self, time):
        if time > self.raise_time:
            return self.amplitude

        # Z twierdzenia talesa o podobieństwie trójkątów
        return (self.amplitude * time) / self.raise_time
    
class SineWave:
    def __init__(self, frequency, amplitude, delay = 0, periods = 6):
        self.amplitude = amplitude
        self.frequency = frequency
        self.delay = delay
        self.periods = periods

    def __str__(self):
        return (
            "Obiekt nieskończonego sygnału harmonicznego, o parametrach: \n"
            "  amplitude - amplituda [V]\n"
            "  frequency - częstotliwość [Hz]\n"
            "  delay - przesunięcie fazy [stopnie]"
        )
    
    def returnStep(self, t_min):
        return min((1 / (self.frequency * 100)), t_min)

    def getSettlingTime(self):
        return -1

    def getValue(self, time):
        return self.amplitude * math.sin(math.radians(self.delay) + 2 * math.pi * self.frequency * time)
    
class TriangleWave:
    def __init__(self, raise_time, fall_time, amplitude):
        self.raise_time = raise_time
        self.fall_time = fall_time
        self.amplitude = amplitude

    def __str__(self):
        return (
            "Obiekt skończonego, pojedynczego sygnału trójkątnego, o prametrach: \n"
            "  raise_time - czas narastania [ms]\n"
            "  fall_time - czas opadania [ms]\n"
            "  amplitude - amplituda [V]"
        )
    
    def returnStep(self, t_min):
        tx1 = self.raise_time / 20
        tx2 = self.fall_time / 20
        tx = tx2 if tx2 < tx1 and self.fall_time != 0 else tx1
        return min(tx, t_min)

    def getValue(self, time):
        # Z twierdzenia talesa o podobieństwie trójkątów
        if time <= self.raise_time:
            return (self.amplitude * time) / self.raise_time
        
        if time > (self.raise_time + self.fall_time):
            return 0

        return (self.amplitude * (self.raise_time + self.fall_time - time)) / self.fall_time
    
    def getSettlingTime(self):
        return self.raise_time + self.fall_time

class Simulator:
    def __init__(self, signal_object, t_min, form, params, ax = None):
        self.signal_object = signal_object
        self.t_min = t_min
        self.ax = ax
        self.form = form

        # --- Odbiór parametrów z GUI ---
        (
            self.a1, self.a0,
            self.b2, self.b1, self.b0,
            self.Kp, self.Tf,
            self.B, self.A,
            self.Umax, self.Umin, self.tolerance, self.start_delay
        ) = params

        self.IAE = 0.0
        self.ISE = 0.0
        self.ITAE = 0.0
        self.ITSE = 0.0

        # --- Konwersja parametrów PID ---
        # Forma klasyczna: A = Ki, B = Kd
        # Forma czasowa:   A = Kp/Ti, B = Kp*Td
        self.Ki = self.A
        self.Kd = self.B

        # --- Dynamiczna transmitancja obiektu ---
        # G(s) = (a1*s + a0) / (b2*s^2 + b1*s + b0)
        Gp = mf.tf([self.a1, self.a0], [self.b2, self.b1, self.b0])
        self.Ap, self.Bp, self.Cp, self.Dp = mf.ssdata(Gp)

        # Stan obiektu
        self.Xp = mf.zeros_vec(len(self.Ap))

        # Dane do wykresu
        self.x_data = []
        self.y_data = []
        self.r_data = []

        # Zmienne PID
        self.I = 0.0
        self.e_prev = 0.0
        self.Df_prev = 0.0

        self.t = 0
        self.error_counter = 0
        self.steady_counter = 0

        self.settling_time = None
        self.metrics_ready = False

    def run(self):
        if getattr(self, "finished", False):
            return False

        # krok czasowy zależny od sygnału wejściowego
        self.step = self.signal_object.returnStep(self.t_min)
        dt = self.step

        ep = 0.001
        if hasattr(self.signal_object, "amplitude"):
            ep = min(ep * self.signal_object.amplitude, ep)

        # Dynamiczne pasmo tolerancji na podstawie amplitudy zadanego sygnału
        amp = getattr(self.signal_object, "amplitude", 1.0)
        # dynamiczny uchyb dopuszczalny (np. 0.05 * 10V = 0.5V)
        ep = self.tolerance * amp 

        # --- 10 kroków RK4 ---
        for _ in range(10):

            # sygnał zadany
            if self.t < self.start_delay:
                r = 0.0
            else:
                r = self.signal_object.getValue(self.t - self.start_delay)

            # wyjście obiektu
            y_mat = mf.matmul(self.Cp, self.Xp)
            y = y_mat[0][0] + self.Dp[0][0] * 0

            # uchyb
            e = r - y

            self.IAE += abs(e) * dt
            self.ISE += (e * e) * dt
            self.ITAE += abs(e) * self.t * dt
            self.ITSE += (e * e) * self.t * dt

            # --- PID ---
            # filtr D (ISA)
            D_raw = (e - self.e_prev) / dt
            alpha = self.Tf / (self.Tf + dt)
            Df = alpha * self.Df_prev + (self.Kd * (1 - alpha)) * D_raw
            self.Df_prev = Df
            self.e_prev = e

            # Surowe sterowanie (potrzebne do sprawdzenia nasycenia)
            u_raw = self.Kp * e + self.Ki * self.I + Df
            
            # Saturacja (ograniczenie fizyczne)
            u = mf.clip(u_raw, self.Umin, self.Umax)

            # Anti-windup (Clamping)
            # Całkujemy TYLKO jeśli sygnał sterujący nie jest ucięty (u_raw == u)
            # ALBO jeśli uchyb e działa w kierunku "odklejenia" od nasycenia (u_raw * e <= 0)
            if u_raw == u or (u_raw * e <= 0):
                self.I += e * dt

            # --- Obiekt (RK4) ---
            self.Xp = mf.rk4_step(self.Ap, self.Bp, self.Xp, u, dt)

            # zapis danych
            self.x_data.append(self.t)
            self.y_data.append(y)
            self.r_data.append(r)

            self.t += dt

            # --- Kryteria stopu i zbieranie metryk ---
            # Jeśli uchyb jest mniejszy bądź równy naszej dopuszczalnej tolerancji:
            if abs(e) <= ep and self.signal_object.getSettlingTime() < (self.t - self.start_delay):
                self.steady_counter += 1
                # Jeśli to pierwszy moment wpadnięcia w pasmo, zapisz potencjalny czas ustalania
                if self.settling_time is None:
                    self.settling_time = self.t 
            else:
                # Sygnał wypadł poza pasmo dopuszczalne - resetujemy liczniki
                self.steady_counter = 0
                self.settling_time = None 

            # Jeśli sygnał utrzymał się w paśmie tolerancji przez 300 kroków, kończymy
            if self.steady_counter > 300 or (isinstance(self.signal_object, SineWave) and (self.signal_object.periods / self.signal_object.frequency) < self.t):
                self.finished = True
                
                # Obliczenia metryk na koniec symulacji
                max_y = max(self.y_data)
                
                # Wyliczamy % przeregulowania (zabezpieczenie przed dzieleniem przez zero)
                if amp != 0:
                    overshoot = ((max_y - amp) / amp) * 100 if max_y > amp else 0.0
                else:
                    overshoot = 0.0
                
                # Zapisujemy ostateczny słownik z danymi dla GUI
                self.metrics = {
                    "step": dt,
                    "final_e": e,
                    "overshoot": overshoot,
                    "settling_time": self.settling_time,
                    "mean_e": self.IAE / self.t if self.t > 0 else 0.0,
                    "is_sine": isinstance(self.signal_object, SineWave)
                }
                self.metrics["IAE"] = self.IAE
                self.metrics["ISE"] = self.ISE
                self.metrics["ITAE"] = self.ITAE
                self.metrics["ITSE"] = self.ITSE
                self.metrics_ready = True
                break

        if (self.ax != None):
            # --- Rysowanie ---
            self.ax.clear()
            self.ax.margins(x=0)
            self.ax.plot(self.x_data, self.r_data, "--", color="red", label="Wejście")
            self.ax.plot(self.x_data, self.y_data, color="blue", label="Wyjście")
            self.ax.set_title("Wykres odpowiedzi układu z regulatorem PID")
            self.ax.set_xlabel("Czas")
            self.ax.set_ylabel("Amplituda")
            self.ax.grid(True, linestyle="--", alpha=0.5)
            self.ax.legend()
            self.ax.figure.canvas.draw()

            if len(self.x_data) > 1:
                self.ax.set_xlim(self.x_data[0], self.x_data[-1])

            if len(self.y_data) > 1:
                ymin = min(self.y_data)
                ymax = max(self.y_data)
                margin = 0.05 * (ymax - ymin if ymax != ymin else 1)
                self.ax.set_ylim(ymin - margin, ymax + margin)

        return not getattr(self, "finished", False)

    def auto_tune(self, quality_params):

        # Punkt startowy
        x0 = [float(self.Kp), float(self.Ki), float(self.Kd), float(self.Tf)]

        # Funkcja celu przekazywana do simplex
        def objective(x):
            Kp, Ki, Kd, Tf = x
            max_Kp = quality_params["max_Kp"]
            max_Ki = quality_params["max_Ki"]
            max_Kd = quality_params["max_Kd"]

            # Ograniczenia: każde wzmocnienie >= 0 i <= max
            if Kp <= 0 or Ki < 0 or Kd < 0 or Tf < 0.02:
                return 1e12
            if Kp > max_Kp or Ki > max_Ki or Kd > max_Kd:
                return 1e12

            params = (
                self.a1, self.a0, self.b2, self.b1, self.b0,
                Kp, Tf, Kd, Ki,
                self.Umax, self.Umin, self.tolerance, self.start_delay
            )

            Sim = Simulator(self.signal_object, self.t_min, self.form, params, ax=None)

            while Sim.run():
                pass

            if not Sim.metrics_ready:
                return 1e12

            # liczymy J
            return mf.pid_cost_function(Sim.metrics, quality_params)

        # Uruchamiamy simplex
        best = mf.nelder_mead(objective, x0, step=0.3, max_iter=40)

        # Ręczne zaokrąglenie z zabezpieczeniem przed zerowym Tf i Kp
        Kp = round(max(0.01, best[0]), 2)
        Ki = round(max(0.0,  best[1]), 2)
        Kd = round(max(0.0,  best[2]), 2)
        Tf = round(max(0.01, best[3]), 2)

        # Zapis do regulatora
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.Tf = Tf
        self.A = Ki
        self.B = Kd

        return Kp, Ki, Kd, Tf

    def get_pid_params(self):
        return self.Kp, self.Tf, self.B, self.A