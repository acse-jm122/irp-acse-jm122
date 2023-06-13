import torch

__all__ = ["Lorenz63", "forwardModel_r"]


def Lorenz63(y, sig, rho, beta):
    """Lorenz '63 model"""
    out = torch.zeros_like(y)
    out[0] = sig * (y[1] - y[0])
    out[1] = y[0] * (rho - y[2]) - y[1]
    out[2] = y[0] * y[1] - beta * y[2]
    return out


def forwardModel_r(xt0: torch.Tensor, time: torch.Tensor,
                   rayleigh, prandtl, b):
    """
    perform integration of Lorentz63 model
    """

    y0 = xt0
    y = torch.empty((xt0.size(0), time.size(0)))
    y[:, 0] = y0
    for i in range(1, int(time.size(0))):
        dy = Lorenz63(y0, prandtl, rayleigh, b)
        y0 = y0 + (time[i] - time[i - 1]) * dy
        y[:, i] = y0
    return y
