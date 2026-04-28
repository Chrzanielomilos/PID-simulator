def matmul(A, B):
    rowsA = len(A)
    colsA = len(A[0])
    rowsB = len(B)
    colsB = len(B[0])

    assert colsA == rowsB, "Dimension mismatch"

    C = [[0.0 for _ in range(colsB)] for _ in range(rowsA)]

    for i in range(rowsA):
        for j in range(colsB):
            for k in range(colsA):
                C[i][j] += A[i][k] * B[k][j]

    return C

def matadd(A, B):
    return [[A[i][j] + B[i][j] for j in range(len(A[0]))] 
            for i in range(len(A))]

def matscale(A, s):
    return [[A[i][j] * s for j in range(len(A[0]))] 
            for i in range(len(A))]

def vecscale(v, s):
    return [[v[i][0] * s] for i in range(len(v))]

def vecadd(a, b):
    return [[a[i][0] + b[i][0]] for i in range(len(a))]

def clip(x, xmin, xmax):
    if x < xmin:
        return xmin
    if x > xmax:
        return xmax
    return x

def zeros_vec(n):
    return [[0.0] for _ in range(n)]

def zeros(n):
    return [0.0 for _ in range(n)]

def ones(n):
    return [1.0 for _ in range(n)]

def mat_from_np(M):
    # konwersja np.array / array-like -> lista list
    return [[float(M[i, j]) for j in range(M.shape[1])] for i in range(M.shape[0])]

def vec_from_np(v):
    # kolumna np.array -> lista [ [v0], [v1], ... ]
    return [[float(v[i, 0])] for i in range(v.shape[0])]

def rk4_step(A, B, x, u, dt):
    # k1 = A*x + B*u
    k1 = vecadd(matmul(A, x), vecscale(B, u))

    # k2 = A*(x + dt/2*k1) + B*u
    x2 = vecadd(x, vecscale(k1, dt * 0.5))
    k2 = vecadd(matmul(A, x2), vecscale(B, u))

    # k3
    x3 = vecadd(x, vecscale(k2, dt * 0.5))
    k3 = vecadd(matmul(A, x3), vecscale(B, u))

    # k4
    x4 = vecadd(x, vecscale(k3, dt))
    k4 = vecadd(matmul(A, x4), vecscale(B, u))

    # x_next = x + dt/6 * (k1 + 2*k2 + 2*k3 + k4)
    sum_k = vecadd(
        vecadd(k1, vecscale(k2, 2)),
        vecadd(vecscale(k3, 2), k4)
    )

    return vecadd(x, vecscale(sum_k, dt / 6.0))

class TransferFunction:
    def __init__(self, num, den):
        # num, den: listy współczynników od najwyższej potęgi s
        # np. (s + 2)/(2 s^2 + 1.5 s + 1) -> num=[1, 2], den=[2, 1.5, 1]
        # normalizacja tak, aby den[0] == 1
        k = den[0]
        self.den = [d / k for d in den]
        self.num = [n / k for n in num]

def tf(num, den):
    return TransferFunction(num, den)

def ssdata(G: TransferFunction):
    """
    Zwraca (A, B, C, D) w formie kanonicznej sterowalnej
    dla SISO G(s) = num(s)/den(s), gdzie:
        den(s) = s^n + a1 s^{n-1} + ... + an
        num(s) = b0 s^n + b1 s^{n-1} + ... + bn
    D = b0
    C = [b1 - a1 D, b2 - a2 D, ..., bn - an D]
    A, B – standardowa forma sterowalna.
    """
    den = G.den[:]  # [1, a1, a2, ..., an]
    num = G.num[:]  # [b0, b1, ..., bm]

    n = len(den) - 1  # rząd układu

    # dopasowanie długości licznika do mianownika (z lewej strony)
    if len(num) < n + 1:
        num = [0.0] * (n + 1 - len(num)) + num
    elif len(num) > n + 1:
        # obcinamy najwyższe, jeśli ktoś podał za długi licznik
        num = num[-(n + 1):]

    # den = [1, a1, a2, ..., an]
    a = den[1:]
    # num = [b0, b1, ..., bn]
    b = num

    #D = b[0]
    ## C = [b1 - a1*D, b2 - a2*D, ..., bn - an*D]
    #C = [[b[i + 1] - a[i] * D for i in range(n)]]

    D = b[0]
    # Poprawiona kolejność: [bn - an*D, b(n-1) - a(n-1)*D, ..., b1 - a1*D]
    C = [[b[n - i] - a[n - 1 - i] * D for i in range(n)]]

    # A – macierz n×n w formie sterowalnej
    A = [[0.0 for _ in range(n)] for _ in range(n)]
    # nadprzekątna = 1
    for i in range(n - 1):
        A[i][i + 1] = 1.0
    # ostatni wiersz = [-an, -a_{n-1}, ..., -a1]
    A[-1] = [-ai for ai in a[::-1]]

    # B – wektor kolumnowy [0, 0, ..., 1]^T
    B = [[0.0] for _ in range(n)]
    B[-1][0] = 1.0

    # D jako 1×1
    D_mat = [[D]]

    return A, B, C, D_mat
