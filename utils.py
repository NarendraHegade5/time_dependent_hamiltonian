import numpy as np
from numpy import pi, exp, sin, cos, sqrt, abs, ceil
from numpy.linalg import solve
from scipy.linalg import eigh_tridiagonal as eigs
from scipy.sparse import csc_matrix, identity
from scipy.sparse.linalg import inv

def get_x(N):
    return np.linspace(1/N, 1-1/N, N-1)

def get_H_bands(N, V):
    x = get_x(N)
    H1 = V(x) + 2*N**2*np.ones(N-1)
    H2 = -N**2*np.ones(N-2)
    return H1, H2

def get_eig(N, V, nev):
    H1, H2 = get_H_bands(N, V)
    l, v = eigs(H1, H2, select="i", select_range=(0,nev-1))
    for i in range(nev):
        if v[1, i]-v[0, i]<0: v[:, i] *= -1
    return l, v

def get_H(N, V):
    H1, H2 = get_H_bands(N, V)
    H = np.concatenate((H1, H2, H2))
    i = np.arange(N-1)
    I = np.concatenate((i, i[:-1:], i[1::]))
    J = np.concatenate((i, i[1::], i[:-1:]))
    return csc_matrix((H, (I, J)))

def f(l, V0):
    k = sqrt(l)
    kappa = sqrt(V0 - l)
    core_p = (kappa*sin(k/3) + k*cos(k/3))**2
    core_m = (kappa*sin(k/3) - k*cos(k/3))**2
    return exp(kappa/3)*core_p - exp(-kappa/3)*core_m

def secant(x1, x2, f, V0, tol=1e-10):
    while True:
        if (x2>=V0): return V0
        if (x2<=0): return 0
        f1 = f(x1, V0) 
        f2 = f(x2, V0)
        if (abs(f2)<tol): return x2
        xnew = x2 - (f2 * (x2 - x1)) / (f2 - f1)
        x1 = x2
        x2 = xnew

def roots(f, dx, V0):
    x = np.array([0, dx, dx+1], dtype=float)
    roots = []
    while True:
        # We want to walk downward before starting secant
        while True:
            fs = f(x, V0)
            if (fs[1]<fs[0] and fs[1]<fs[2]): break
            x += dx
            if (x[2]>=V0): return roots

        # Know there are two roots near bottom
        roots.append(secant(x[0], x[1], f, V0))
        # "heuristic", also known as a hack. For low V0

        while (f(x[2], V0)<0 and x[2]+dx<V0): x+=dx
        roots.append(secant(x[1], x[2], f, V0))
        x += 1.
        if (x[2]>=V0): return roots

def time_evolve(v, l, T, alpha=np.array([1])):
    n = len(alpha)
    C = alpha*exp(-1j*l[0:n]*T)
    return np.einsum("ij, j -> i", v, C)

def euler_step(N, V, dt):
    H = get_H(N, V)
    I = identity(N-1, format="csc")
    return I - 1j*dt*H

def pade_step(N, V, dt):
    H = get_H(N, V)
    I = identity(N-1, format="csc")
    H1 =  I-1j/2*dt*H
    H2 = inv(I+1j/2*dt*H)
    return H2@H1

def inner(u, v):
    return np.dot(np.conj(u), v)

def get_tau(N, l0, v0, V_Vr, Vr):
    H = get_H(N, lambda x: V_Vr(x, Vr))
    return inner(v0[:, 0], H@v0[:, 1])

def get_H_eff(N, l0, v0, V_Vr, Vr):
    tau = get_tau(N, l0, v0, V_Vr, Vr)
    eps = l0[1] - l0[0]
    return np.array([
        [-eps/2, tau],
        [tau, eps/2]
    ])

def get_HI(N, T, tau, w):
    t = np.linspace(0, T, N)
    a = tau*sin(w*t)
    H = np.array([
        [np.zeros(N), exp(-1j*t)*a],
        [exp(+1j*t)*a, np.zeros(N)], 
    ])
    return np.moveaxis(H, -1, 0)

def solve_psi(v0, N, H, dt):
    v = np.zeros((N, 2), dtype=np.complex_)
    v[0] = v0

    for k in range(1, N):
        A = np.identity(2) - 1j*dt*H[k]
        b = v0 - 1j*dt*np.einsum("kij, kj -> i", H[:k], v[:k])
        v[k] = solve(A, b)

    return v

def get_psi_t(v0, N, T, tau, w):
    dt = T/N
    H = get_HI(N, T, tau, w, )
    return solve_psi(v0, N, H, dt)

def get_prob(v0, N, T, tau, w):
    v = get_psi_t(v0, N, T, tau, w)
    p = np.empty(N)
    for k in range(N):
        p[k] = 1 - abs(inner(v0, v[k]))**2
    return p
