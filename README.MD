![Build and test](https://github.com/Chrzanielomilos/PID-simulator/actions/workflows/build.yml/badge.svg)


# TODO:
Wstawić obrazki wzorów z Latext do MD i do okienka aplikacji
# **Symulator odpowiedzi układu z regulatorem PID**

Interaktywny symulator napisany w Pythonie z wykorzystaniem **Tkinter** i **Matplotlib**, umożliwiający analizę odpowiedzi układów dynamicznych drugiego rzędu sterowanych regulatorem PID z filtrem na członie D.  
Aplikacja pozwala na dobór parametrów transmitancji, konfigurację regulatora oraz wybór sygnału wejściowego.

---

## **Funkcjonalności**

- Konfiguracja transmitancji obiektu:
\[
  G_0(s) = \frac{a_1 s + a_0}{b_2 s^2 + b_1 s + b_0}
  \]


- Wybór formy regulatora PID:
  - **klasyczna** (Kp, Ki, Kd)
  - **czasowa** (Kp, Ti, Td)
- Obsługa sygnałów wejściowych:
  - impuls jednostkowy (aproksymacja delty Diraca)
  - rampa
  - skończony prostokąt
  - sinusoidalny
  - trójkątny
- Dynamiczna symulacja z wykorzystaniem metody **Runge–Kutta 4 rzędu**
- Automatyczne dobieranie kroku czasowego na podstawie najmniejszej stałej czasowej
- Inteligentne warunki zakończenia symulacji
- Możliwość ręcznego zatrzymania symulacji przyciskiem **STOP**
- Wizualizacja sygnału wejściowego i wyjściowego w czasie rzeczywistym

---

## **Struktura projektu**

```
├── main.py              # Główne GUI aplikacji (Tkinter)
├── matFunctions.py      # Logika obliczeniowa i modele sygnałów
├── README.md            # Dokumentacja projektu
```

---

## **Wymagania**

- Python 3.13
- Biblioteki:
  - requirements.txt

### Pierwsze uruchomienie: (Linux)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## **Uruchomienie aplikacji**

W katalogu projektu:
### Linux
```bash
source ./venv/bin/activate
python symulator.py
```

Aplikacja otworzy okno GUI z panelem sterowania i wykresem.

---

## **Opis działania symulatora**

### 1. **Wybór parametrów obiektu**
Użytkownik podaje wartości:
- a1, a0 — licznik transmitancji  
- b2, b1, b0 — mianownik transmitancji  

Parametry są walidowane (np. b2 ≠ 0).

---

### 2. **Konfiguracja regulatora PID**

Dostępne są dwie formy:

#### Forma klasyczna:
- Kp — wzmocnienie proporcjonalne  
- Ki — wzmocnienie całkujące  
- Kd — wzmocnienie różniczkujące  

#### Forma czasowa:
- Kp — wzmocnienie proporcjonalne  
- Ti — stała czasowa całkowania  
- Td — stała czasowa różniczkowania  

Parametry są automatycznie przeliczane na wartości używane w równaniach stanu.

---

### 3. **Wybór sygnału wejściowego**

Każdy sygnał ma własną klasę i metodę `getValue(t)`:

| Sygnał | Opis |
|--------|------|
| Impuls jednostkowy | Aproksymacja delty Diraca jako wąski impuls |
| Rampa | Narastanie liniowe |
| Prostokąt | Sygnał o skończonym czasie trwania |
| Sinus | Sygnał harmoniczny |
| Trójkątny | Narastanie i opadanie liniowe |

---

### 4. **Symulacja**

Symulator korzysta z:

- metody **RK4** do rozwiązywania równań stanu,
- adaptacyjnego kroku czasowego,
- warunków stopu opartych na:
  - stabilizacji pochodnej,
  - błędzie regulacji,
  - czasie trwania sygnału.

Wyniki są rysowane na wykresie w czasie rzeczywistym.

---

## **Model regulatora PID**

Regulator opisany jest równaniami stanu:

\[
u = K_p e + I + u_D
\]

\[
\dot{I} = K_i e
\]

\[
\dot{u_D} = \frac{K_d \dot{e} - u_D}{T_f}
\]

gdzie:
- \( e = r - y \)
- \( r(t) \) — sygnał wejściowy  
- \( y(t) \) — wyjście obiektu  

---

## **Wizualizacja**

Wykres przedstawia:

- sygnał wejściowy (czerwony, przerywany)  
- sygnał wyjściowy (niebieski)  

Dla delty Diraca rysowany jest punkt w t = 0.

---

## **Zatrzymywanie symulacji**

Przycisk **STOP** ustawia:

```python
self.Sim.finished = True
```

co natychmiast przerywa pętlę `tick()`.

---

## **Przykładowy przebieg**

- ustaw Kp = 1, Ki = 1, Kd = 0.1  
- wybierz sygnał prostokątny 50 ms  
- obserwuj odpowiedź układu drugiego rzędu z PID  

---

## **Licencja**

Projekt może być używany i modyfikowany zgodnie z zasadami ustalonymi przez autora.
