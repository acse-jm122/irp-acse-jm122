import torch
from typing import Callable

__all__ = ["apply_3DVar", "apply_4DVar"]


def apply_3DVar(
    H: Callable,
    B: torch.Tensor,
    R: torch.Tensor,
    xb: torch.Tensor,
    y: torch.Tensor,
    threshold: float = 1e-5,
    max_iterations: int = 1000,
    learning_rate: float = 1e-3,
    is_vector_xb: bool = True,
    batch_first: bool = True,
    logging: bool = True,
) -> torch.Tensor:
    """
    apply 3DVar
    """
    new_x0 = torch.nn.Parameter(xb.clone().detach())

    def J(x0: torch.Tensor, xb: torch.Tensor, y: torch.Tensor):
        x0_minus_xb = x0 - xb
        y_minus_H_x0 = y - H(x0)
        return (
            x0_minus_xb.reshape((1, -1)) @
            torch.linalg.solve(B, x0_minus_xb).reshape((-1, 1))
            + y_minus_H_x0.reshape((1, -1)) @
            torch.linalg.solve(R, y_minus_H_x0).reshape((-1, 1))
        )

    trainer = torch.optim.Adam([new_x0], lr=learning_rate)
    for n in range(max_iterations):
        trainer.zero_grad(set_to_none=True)
        if is_vector_xb:
            loss = J(new_x0, xb, y)
        else:
            loss = 0
            sequence_length = xb.size(1) if batch_first else xb.size(0)
            for i in range(sequence_length):
                one_x0, one_xb = (
                    (new_x0[:, i], xb[:, i]) if batch_first
                    else (new_x0[i], xb[i])
                )
                loss += J(one_x0.ravel(), one_xb.ravel(), y[i])
        loss.backward(retain_graph=True)
        grad_norm = torch.norm(new_x0.grad)
        if logging:
            print(
                f"Iterations: {n}, J: {loss.item()}, "
                f"Norm of J gradient: {grad_norm.item()}"
            )
        if grad_norm <= threshold:
            break
        trainer.step()

    return new_x0.detach()


def apply_4DVar(
    nobs: int,
    time_obs: torch.Tensor,
    gap: int,
    M: Callable,
    H: Callable,
    B: torch.Tensor,
    R: torch.Tensor,
    xb: torch.Tensor,
    y: torch.Tensor,
    start_time: float = 0.0,
    model_args: tuple = (None,),
    threshold: float = 1e-5,
    max_iterations: int = 1000,
    learning_rate: float = 1e-3,
    is_vector_xb: bool = True,
    is_vector_y: bool = True,
    batch_first: bool = True,
    logging: bool = True,
) -> torch.Tensor:
    """
    apply 4DVar
    """
    new_x0 = torch.nn.Parameter(xb.clone().detach())

    # def Jb(x0: torch.Tensor, xb: torch.Tensor):
    #     x0_minus_xb = x0 - xb
    #     return (
    #         x0_minus_xb.reshape((1, -1)) @
    #         torch.linalg.solve(B, x0_minus_xb).reshape((-1, 1))
    #     )

    def Jb(x0: torch.Tensor, xb: torch.Tensor, y: torch.Tensor):
        x0_minus_xb = x0 - xb
        y_minus_H_x0 = y - H(x0)
        return (
            x0_minus_xb.reshape((1, -1)) @
            torch.linalg.solve(B, x0_minus_xb).reshape((-1, 1))
            + y_minus_H_x0.reshape((1, -1)) @
            torch.linalg.solve(R, y_minus_H_x0).reshape((-1, 1))
        )

    def Jo(xp: torch.Tensor, y: torch.Tensor):
        y_minus_H_xp = y - H(xp)
        return (
            y_minus_H_xp.reshape((1, -1)) @
            torch.linalg.solve(R, y_minus_H_xp).reshape((-1, 1))
        )

    trainer = torch.optim.Adam([new_x0], lr=learning_rate)
    for n in range(max_iterations):
        trainer.zero_grad(set_to_none=True)
        current_time = start_time
        if is_vector_xb:
            total_loss = Jb(new_x0, xb, y[0])
        else:
            total_loss = 0
            sequence_length = xb.size(1) if batch_first else xb.size(0)
            for i in range(sequence_length):
                one_x0, one_xb = (
                    (new_x0[:, i], xb[:, i]) if batch_first
                    else (new_x0[i], xb[i])
                )
                total_loss += Jb(one_x0.ravel(), one_xb.ravel(), y[0, i])
        xp = new_x0
        for iobs in range(1, nobs):
            time_fw = torch.linspace(
                current_time, time_obs[iobs - 1], gap + 1, device=xb.device
            )
            if is_vector_y:
                xf = M(xp, time_fw, *model_args)
                xp = xf[:, -1]
                total_loss += Jo(xp, y[iobs])
            else:
                xp = M(xp, time_fw, *model_args)
                sequence_length = xp.size(1) if batch_first else xp.size(0)
                for i in range(sequence_length):
                    one_xp = xp[:, i] if batch_first else xp[i]
                    total_loss += Jo(one_xp.ravel(), y[iobs, i])
            current_time = time_obs[iobs - 1]
        total_loss.backward(retain_graph=True)
        grad_norm = torch.norm(new_x0.grad)
        if logging:
            print(
                f"Iterations: {n}, J: {total_loss.item()}, "
                f"Norm of J gradient: {grad_norm.item()}"
            )
        if grad_norm <= threshold:
            break
        trainer.step()

    return new_x0.detach()
