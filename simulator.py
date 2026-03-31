import math
import numpy as np
import mathFunctions as mf

class FiniteSquare:
    def __init__(self, duration, amplitude):
        self.amplitude = amplitude
        self.duration = duration / 1000

    def __str__(self):
        return (
            "Obiekt skończonego, pojedynczego sygnału prostokątnego o parametrach \n"
            "  amplitude - amplituda [V]\n"
            "  duration - czas trwania wartości wysokiej sygnału [ms]\n"
        )
    
    def returnStep(self, t_min):
        return min((self.duration / 20), t_min)

    def getValue(self, time):
        if time > self.duration:
            return 0

        return self.amplitude

class Ramp:
    def __init__(self, raise_time, amplitude):
        self.raise_time = raise_time / 1000
        self.amplitude = amplitude

    def __str__(self):
        return (
            f"Sygnał rampy o parametrach:\n"
            f"  rise_time - czas narastania [ms]\n"
            f"  amplitude - amplituda [V]\n"
        )
    
    def returnStep(self, t_min):
        return min((self.raise_time / 20), t_min)

    def getValue(self, time):
        if time > self.raise_time:
            return self.amplitude

        # Z twierdzenia talesa o podobieństwie trójkątów
        return (self.amplitude * time) / self.raise_time
    
class SineWave:
    def __init__(self, frequency, amplitude, delay = 0):
        self.amplitude = amplitude
        self.frequency = frequency
        self.delay = delay

    def __str__(self):
        return (
            "Obiekt nieskończonego sygnału harmonicznego, o parametrach: \n"
            "  amplitude - amplituda [V]\n"
            "  frequency - częstotliwość [Hz]\n"
            "  delay - przesunięcie fazy [stopnie]"
        )
    
    def returnStep(self, t_min):
        return min((1 / (self.frequency * 20)), t_min)

    def getValue(self, time):
        return self.amplitude * math.sin(np.deg2rad(self.delay) + 2 * np.pi * self.frequency * time)
    
class TriangleWave:
    def __init__(self, raise_time, fall_time, amplitude):
        self.raise_time = raise_time / 1000
        self.fall_time = fall_time / 1000
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

class Simulator:
    def __init__(self, signal_object, t_min, ax, form, params):
        self.signal_object = signal_object
        self.t_min = t_min
        self.ax = ax
        self.form = form

        # --- Odbiór parametrów z GUI ---
        (
            self.a1, self.a0,
            self.b2, self.b1, self.b0,
            self.Kp, self.Tf,
            self.B, self.A
        ) = params

        # --- Konwersja parametrów PID ---
        # Forma klasyczna: A = Ki, B = Kd
        # Forma czasowa:   A = Kp/Ti, B = Kp*Td
        self.Ki = self.A
        self.Kd = self.B

        # --- Saturacja (na razie stała, później dodasz w GUI) ---
        self.Umax = 1.0

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

    def run(self):
        if getattr(self, "finished", False):
            return False

        # krok czasowy zależny od sygnału wejściowego
        self.step = self.signal_object.returnStep(self.t_min)
        dt = self.step

        ep = 0.001
        if hasattr(self.signal_object, "amplitude"):
            ep = min(ep * self.signal_object.amplitude, ep)

        # --- 10 kroków RK4 ---
        for _ in range(10):

            # sygnał zadany
            r = self.signal_object.getValue(self.t)

            # wyjście obiektu
            y_mat = mf.matmul(self.Cp, self.Xp)
            y = y_mat[0][0] + self.Dp[0][0] * 0

            # uchyb
            e = r - y

            # --- PID ---
            self.I += e * dt

            # filtr D (ISA)
            D_raw = (e - self.e_prev) / dt
            alpha = self.Tf / (self.Tf + dt)
            Df = alpha * self.Df_prev + (self.Kd * (1 - alpha)) * D_raw
            self.Df_prev = Df
            self.e_prev = e

            # sterowanie
            u = self.Kp * e + self.Ki * self.I + Df
            u = mf.clip(u, -self.Umax, self.Umax)

            # --- Obiekt (RK4) ---
            self.Xp = mf.rk4_step(self.Ap, self.Bp, self.Xp, u, dt)

            # zapis danych
            self.x_data.append(self.t)
            self.y_data.append(y)
            self.r_data.append(r)

            self.t += dt

            # --- Kryteria stopu ---
            if abs(e) < ep:
                self.error_counter += 1
            else:
                self.error_counter = 0

            if abs(y) < ep:
                self.steady_counter += 1
            else:
                self.steady_counter = 0

            if self.error_counter > 200 or self.steady_counter > 200:
                self.finished = True
                break

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
