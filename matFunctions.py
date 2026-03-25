import math
import numpy as np

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

class DirracDelta:
    def __init__(self, width=0.001):
        self.width = width

    def __str__(self):
        return (
            "Obiekt impulsu jednostkowego delty dirraca \n"
        )

    def returnStep(self, t_min):
        return min(self.width / 10, t_min)

    def getValue(self, time):
        return 1 / self.width if time < self.width else 0
        return int(time == 0)

class Simulator:
    def __init__(self, signal_object, t_min, ax, form, params):
        self.signal_object = signal_object
        self.t_min = t_min
        self.ax = ax

        # Parametry układu
        self.a1, self.a0, self.b2, self.b1, self.b0, self.Kp, self.Tf, self.B, self.A = params

        # Punkt początkowy
        self.x_data = []
        self.y_data = []
        self.r_data = []

        self.x = [0, 0, 0, 0]
        self.t = 0

        self.error_counter = 0
        self.steady_counter = 0


    def __str__(self):
        return (
            "Obiekt symulatora, przy tworzeniu przyjmuje obiekt sygnału wejściowego oraz najmniejszą stałą czasową układu i obiekt wykresu\n"
        )

    def derivative(self, f, t):
        """Numeryczna pochodna sygnału wejściowego r(t)."""
        if isinstance(self.signal_object, DirracDelta):
            return 0.0
        return (f(t + self.step) - f(t)) / self.step

    def integrate(self, value, previous, dt):
        """Prosta całka Eulera."""
        return previous + value * dt

    def rk4(self, t, x):
        dt = self.step

        k1 = self.state_derivatives(t, x)
        k2 = self.state_derivatives(t + dt/2, [xi + dt/2*k1i for xi, k1i in zip(x, k1)])
        k3 = self.state_derivatives(t + dt/2, [xi + dt/2*k2i for xi, k2i in zip(x, k2)])
        k4 = self.state_derivatives(t + dt,   [xi + dt*k3i   for xi, k3i in zip(x, k3)])

        return [
            xi + dt/6 * (k1i + 2*k2i + 2*k3i + k4i)
            for xi, k1i, k2i, k3i, k4i in zip(x, k1, k2, k3, k4)
        ]

    def state_derivatives(self, t, x):
        x1, x2, x3, x4 = x   # y, y', I, u_D

        r  = self.signal_object.getValue(t)
        dr = self.derivative(self.signal_object.getValue, t)

        e  = r - x1
        de = dr - x2

        # PID
        dx3 = self.A * e                     # A = Ki
        dx4 = (self.B * de - x4) / self.Tf   # B = Kd

        u = self.Kp * e + x3 + x4

        # pochodna sterowania
        du = self.Kp * de + dx3 + dx4

        # obiekt
        dx1 = x2
        dx2 = (self.a1 * du + self.a0 * u - self.b1 * x2 - self.b0 * x1) / self.b2

        return [dx1, dx2, dx3, dx4]

    def run(self):
        """Wykonuje 10 kroków symulacji i zwraca True jeśli symulacja trwa dalej."""
        
        # jeśli symulacja już zakończona — nic nie rób
        if getattr(self, "finished", False):
            return False

        self.step = self.signal_object.returnStep(self.t_min)
        ep = 0.001
        if not isinstance(self.signal_object, DirracDelta):
            ep1 = ep * self.signal_object.amplitude
            ep = ep1 if ep1 < ep else ep

        # wykonaj 10 kroków RK4
        for _ in range(10):

            # 1 krok RK4
            self.x = self.rk4(self.t, self.x)
            y = self.x[0]
            r = self.signal_object.getValue(self.t)
            self.r_data.append(r)

            # zapis danych
            self.x_data.append(self.t)
            self.y_data.append(y)
            self.t += self.step

            if isinstance(self.signal_object, SineWave):
                # ograniczenie do kilku okresów
                if self.t > (4 / self.signal_object.frequency):
                    self.finished = True
                    break
            else:
                if self.t < (100 * self.step):
                    continue

                if not isinstance(self.signal_object, DirracDelta):
                    if self.t > self.signal_object.duration:  # dopiero po zakończeniu sygnału
                        if abs(self.x[1]) < ep:
                            self.steady_counter += 1
                        else:
                            self.steady_counter = 0

                # kryterium błędu
                e = abs(r - y)
                if e < ep:
                    self.error_counter += 1
                else:
                    self.error_counter = 0

                # warunek stopu
                if self.steady_counter > 200 or self.error_counter > 200:
                    self.finished = True
                    break

        # aktualizacja wykresu po 10 krokach
        self.ax.clear()
        self.ax.margins(x=0)
        self.ax.plot(self.x_data, self.y_data, color="blue", label="Wyjście")
        if isinstance(self.signal_object, DirracDelta):
            self.ax.scatter([0], [1], color="red", marker="o")
        else:
            self.ax.plot(self.x_data, self.r_data, alpha=0.8, color="red", linestyle="--", label="Wejście")
        self.ax.set_title("Wykres odpowiedzi układu z regulatorem PID")
        self.ax.set_xlabel("Czas")
        self.ax.set_ylabel("Amplituda")
        self.ax.grid(True, linestyle="--", alpha=0.5)
        self.ax.legend()
        self.ax.figure.canvas.draw()

        # ustawienie zakresu osi X bez pustych marginesów
        if len(self.x_data) > 1:
            self.ax.set_xlim(self.x_data[0], self.x_data[-1])

        # ustawienie zakresu osi Y bez pustych marginesów
        if len(self.y_data) > 1:
            ymin = min(self.y_data)
            ymax = max(self.y_data)

            # mały margines, żeby linia nie dotykała krawędzi
            margin = 0.05 * (ymax - ymin if ymax != ymin else 1)

            self.ax.set_ylim(ymin - margin, ymax + margin)

        # zwróć informację, czy symulacja ma trwać dalej
        return not getattr(self, "finished", False)
