![Build and test](https://github.com/Chrzanielomilos/PID-simulator/actions/workflows/build.yml/badge.svg)

---

# Symulator odpowiedzi układu z regulatorem PID — dokumentacja implementacji

Poniższa dokumentacja opisuje tylko i wyłącznie zachowanie i strukturę tego konkretnego symulatora, tak jak zostało zaimplementowane w plikach `main.py`, `simulator.py`, `mathFunctions.py` i `tooltip.py`.

---

## Cel projektu

Interaktywny symulator układu drugiego rzędu sterowanego regulatorem PID z filtrem D i prostym anty-windup. Pozwala na ręczną konfigurację transmitancji, parametrów PID, ograniczeń saturacji oraz wyboru sygnału wejściowego, a także uruchomienie automatycznego strojenia (Nelder–Mead) wykorzystującego miary z symulacji.

---

## Pliki i ich rola

- `main.py` — GUI (Tkinter): pola wejściowe, walidacja, wywołania `Simulator`, okno auto-regulacji, logi i rysowanie wykresu.
- `simulator.py` — klasy sygnałów (`Ramp`, `FiniteSquare`, `SineWave`, `TriangleWave`) oraz `Simulator` realizujący: integrację (RK4), PID, saturację, anty-windup, zbieranie metryk i auto-strojenie (Nelder–Mead).
- `mathFunctions.py` — operacje macierzowe, `rk4_step`, funkcje `tf` i `ssdata` (przekształcenie TF->A,B,C,D), funkcja kosztu `pid_cost_function` i implementacja `nelder_mead`.
- `tooltip.py` — helper do wyświetlania podpowiedzi w GUI.

---

## Jak uruchomić

1. Utwórz i aktywuj virtualenv, zainstaluj zależności z `requirements.txt`.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## Dokładny model obiektu użyty w symulatorze

Transmitancja:

$$
G_0(s)=\frac{a_1 s + a_0}{b_2 s^2 + b_1 s + b_0}
$$

W kodzie (`simulator.py`) ta transmitancja jest konwertowana do postaci stanu (A,B,C,D) przez `mf.tf(...)` i `mf.ssdata(...)`.

---

## Szczegóły implementacji regulatora PID

- Równanie sterowania w pętli symulacji (`Simulator.run`):

  - $D_{raw} = \frac{e - e_{prev}}{dt}$
  - $\alpha = \frac{T_f}{T_f + dt}$
  - $Df = \alpha D_{f_{prev}} + (K_d(1 - \alpha))D_{raw}$
  - $u_{raw} = K_p e + K_i I + D_f$
  - $u = clip(u_{raw}, U_{min}, U_{max})$

- Interpretacja parametrów przekazywanych do `Simulator` (parametr `params` w `main.py`):

  `[a1, a0, b2, b1, b0, Kp, Tf, B, A, Umax, Umin, tolerance]`

  gdzie w kodzie `A` = `Ki` (jeśli forma klasyczna) lub `Kp/Ti` (jeśli forma czasowa), oraz `B` = `Kd` (klasyczna) lub `Kp*Td` (czasowa).

---

## Filtr na wyjściu członu różniczkującego

- Filtr D implementowany jest jako jednoparametrowy filtr IIR z parametrem `alpha = Tf/(Tf+dt)` i wykorzystaniem poprzedniej wartości `Df_prev` (patrz wyżej). `Tf` pochodzi z GUI (`self.pid_vars['Tf']`).

---

## Saturacja i anty-windup

- Saturacja: `u = mf.clip(u_raw, Umin, Umax)`.
- Anty-windup (clamping): całka `I` jest aktualizowana tylko, gdy `u_raw == u` (nie było cięcia) lub gdy `u_raw * e <= 0` (uchyb działa w kierunku odklejenia od nasycenia). W przeciwnym razie `I` nie jest aktualizowane.

---

## Integracja i dobór kroku

- Integracja stanu obiektu wykonywana jest funkcją `mf.rk4_step` (RK4).
- Krok `dt` jest dobierany automatycznie na podstawie najmniejszej stałej czasowej. Przez to warto przed uruchomieniem autoregulacji wprowadzić równy punkt początkowy regulatora, ponieważ sam proces strojenia odbędzie się wtedy szybciej.

---

## Sygnały wejściowe

- `FiniteSquare(duration, amplitude)`
- `Ramp(raise_time, amplitude)`
- `SineWave(frequency, amplitude, delay=0)`
- `TriangleWave(raise_time, fall_time, amplitude)`


---

## Metryki

- `IAE`, `ISE`, `ITAE`, `ITSE` kumulowane w pętli.
- Przy zakończeniu symulacji `Simulator.metrics` zawiera: `step`, `final_e`, `overshoot`, `settling_time`, `IAE`, `ISE`, `ITAE`, `ITSE`.

---

## Kryteria stopu

- Główna reguła zakończenia: jeśli uchyb `abs(e) <= ep` (gdzie `ep = tolerance * amplitude`) i `signal_object.getSettlingTime() < t`, to inkrementowany jest `steady_counter`.
- Jeśli `steady_counter > 300` symulacja zostaje zakończona.
- Dla `SineWave` dodatkowy warunek: symulacja kończy się, gdy `t > 6 / frequency` (po 6 okresach).

---

## Auto-strojenie

- Optymalizator: lokalna implementacja Nelder–Mead z wykorzystaniem funkcji kary. `Simulator.auto_tune` wywołuje ją z parametrami `step=0.3` i `max_iter=40`.
- Punkt startowy używany przez optymalizator to wektor trzech parametrów: `x0 = [Kp, Ki, Kd]` (z aktualnych wartości regulatora). Parametr `Tf` NIE jest optymalizowany przez obecną implementację.

- Funkcja celu (`objective`) — dokładny przebieg:
  1. Przyjmuje testowane wartości `x = [Kp, Ki, Kd]`.
  2. Sprawdza ograniczenia twarde: `Kp <= 0` lub `Ki < 0` lub `Kd < 0` zwracają karę `1e12`. Dodatkowo sprawdza, czy nie przekroczono górnych limitów `max_Kp`, `max_Ki`, `max_Kd` (wartości z GUI) — naruszenie również daje `1e12`.
  3. Tworzy tymczasowy `Simulator` z tymi parametrami i uruchamia go w pętli (`while Sim.run(): pass`).
  4. Po zakończeniu pobiera `Sim.metrics` i oblicza wartość funkcji kosztu wywołaniem `mathFunctions.pid_cost_function(Sim.metrics, quality_params)`.

- Po zakończeniu optymalizacji najlepszy wektor `best` jest zaokrąglany do dwóch miejsc i przypisywany jako nowe `Kp, Ki, Kd` (oraz zapisywany w `self.A`, `self.B` w celu dalszego użycia). `main.py` następnie aktualizuje pola GUI.

### Kryteria jakości (dokładne rozwinięcia i wzory)

W kodzie dostępne są cztery typy funkcji kosztu — to dokładnie te, które można wybrać w GUI (`IAE`, `ISE`, `ITAE`, `ITSE`) i które są rozpoznawane przez `mathFunctions.pid_cost_function`:

- IAE — Integral of Absolute Error (całka modułu uchybu):

  $$
  J_{\mathrm{IAE}} = \int_{0}^{T} |e(t)|dt
  $$

  W wersji dyskretnej:

  $$
  \sum_{t=0}^{T}{|e(t)|dt}
  $$

- ISE — Integral of Squared Error (całka kwadratu uchybu):

  $$
  J_{\mathrm{ISE}} = \int_{0}^{T} e^2(t)dt
  $$

  W wersji dyskretnej:
  $$
  \sum_{t=0}^{T}{e^2(t)dt}
  $$

- ITAE — Integral of Time-weighted Absolute Error (całka czasu razy moduł uchybu):

  $$
  J_{\mathrm{ITAE}} = \int_{0}^{T} t|e(t)|dt
  $$

  W wersji dyskretnej:
  $$
  \sum_{t=0}^{T}{t|e(t)|dt}
  $$

- ITSE — Integral of Time-weighted Squared Error (całka czasu razy kwadrat uchybu):

  $$
  J_{\mathrm{ITSE}} = \int_{0}^{T} te^2(t)dt
  $$

  W wersji dyskretnej: `e*e * t * dt`).
  $$
  \sum_{t=0}^{T}{te^2(t)dt}
  $$

W `mathFunctions.pid_cost_function(metrics, quality_params)` wybierany jest dokładnie jeden z tych czterech wskaźników według `quality_params['cost_function']` i jest on zwracany jako wartość J minimalizowana przez Nelder–Mead.
