import torch
from ignite.engine.engine import Engine
from ignite.utils import convert_tensor
from bonsai.pruning.abstract_pruners import AbstractPruner, GradBasedPruner
# import logging
#
# logging.basicConfig(level=logging.DEBUG)


def _prepare_batch(batch, device=None, non_blocking=False):
    """Prepare batch for training: pass to a device with options.

    """
    x, y = batch
    return (convert_tensor(x, device=device, non_blocking=non_blocking),
            convert_tensor(y, device=device, non_blocking=non_blocking))


def create_supervised_trainer(model, optimizer, loss_fn,
                              device=None, non_blocking=False,
                              prepare_batch=_prepare_batch,
                              output_transform=lambda x, y, y_pred, loss: loss.item()):
    """
    Factory function for creating a trainer for supervised models.

    Args:
        model (`torch.nn.Module`): the model to train.
        optimizer (`torch.optim.Optimizer`): the optimizer to use.
        loss_fn (torch.nn loss function): the loss function to use.
        device (str, optional): device type specification (default: None).
            Applies to both model and batches.
        non_blocking (bool, optional): if True and this copy is between CPU and GPU, the copy may occur asynchronously
            with respect to the host. For other cases, this argument has no effect.
        prepare_batch (callable, optional): function that receives `batch`, `device`, `non_blocking` and outputs
            tuple of tensors `(batch_x, batch_y)`.
        output_transform (callable, optional): function that receives 'x', 'y', 'y_pred', 'loss' and returns value
            to be assigned to engine's state.output after each iteration. Default is returning `loss.item()`.

    Note: `engine.state.output` for this engine is the loss of the processed batch.

    Returns:
        Engine: a trainer engine with supervised update function.
    """
    if device:
        model.to(device)

    def _update(engine, batch):
        model.train()
        optimizer.zero_grad()
        x, y = prepare_batch(batch, device=device, non_blocking=non_blocking)
        y_pred = model(x)
        if isinstance(loss_fn, list):
            assert len(y_pred) == len(y) == len(loss_fn), \
                "If loss_fn is a list, its length should match the number of outputs and labels"
            loss = sum(loss_fn[i](y_pred[i], y[i]) for i in range(len(loss_fn)))
        else:
            loss = sum([loss_fn(y_pred[i], y) for i in range(len(y_pred))])
        loss.backward()
        optimizer.step()
        return output_transform(x, y, y_pred, loss)

    return Engine(_update)


def create_supervised_evaluator(model, metrics={},
                                device=None, non_blocking=True,
                                prepare_batch=_prepare_batch,
                                output_transform=lambda x, y, y_pred: (y_pred, y,)):
    """
    Factory function for creating an evaluator for supervised models.

    Args:
        model (`torch.nn.Module`): the model to train.
        metrics (dict of str - :class:`~ignite.metrics.Metric`): a map of metric names to Metrics.
        device (str, optional): device type specification (default: None).
            Applies to both model and batches.
        non_blocking (bool, optional): if True and this copy is between CPU and GPU, the copy may occur asynchronously
            with respect to the host. For other cases, this argument has no effect.
        prepare_batch (callable, optional): function that receives `batch`, `device`, `non_blocking` and outputs
            tuple of tensors `(batch_x, batch_y)`.
        output_transform (callable, optional): function that receives 'x', 'y', 'y_pred' and returns value
            to be assigned to engine's state.output after each iteration. Default is returning `(y_pred, y,)` which fits
            output expected by metrics. If you change it you should use `output_transform` in metrics.

    Note: `engine.state.output` for this engine is a tuple of `(batch_pred, batch_y)`.

    Returns:
        Engine: an evaluator engine with supervised inference function.
    """
    if device:
        model.to(device)

    def _inference(engine, batch):
        model.eval()
        with torch.no_grad():
            x, y = prepare_batch(batch, device=device, non_blocking=non_blocking)
            y_pred = model(x)
            return output_transform(x, y, y_pred)

    engine = Engine(_inference)

    for name, metric in metrics.items():
        metric.attach(engine, name)

    return engine


# TODO needs documentation
def create_supervised_ranker(model, prunner: AbstractPruner, loss_fn,
                             device=None, non_blocking=True,
                             prepare_batch=_prepare_batch,
                             output_transform=lambda x, y, y_pred, loss: loss.item()):
    """
    Factory function for creating a ranker for supervised models

    Args:
        model (`torch.nn.Module`): the model to train
        prunner (`torch.optim.Optimizer`): the optimizer to use
        loss_fn (torch.nn loss function): the loss function to use
        device (str, optional): device type specification (default: None).
            Applies to both model and batches.
        non_blocking (bool, optional): if True and this copy is between CPU and GPU, the copy may occur asynchronously
            with respect to the host. For other cases, this argument has no effect.
        prepare_batch (Callable, optional): function that receives `batch`, `device`, `non_blocking` and outputs
            tuple of tensors `(batch_x, batch_y)`.
        output_transform (callable, optional): function that receives 'x', 'y', 'y_pred', 'loss' and returns value
            to be assigned to engine's state.output after each iteration. Default is returning `loss.item()`.

    Returns:
        Engine: a trainer engine with supervised update function
    """
    if device:
        model.to(device)

    def _update(engine, batch):
        model.train()
        x, y = prepare_batch(batch, device, non_blocking=non_blocking)
        y_pred = model(x)
        if isinstance(loss_fn, list):
            assert len(y_pred) == len(y) == len(loss_fn), \
                "If loss_fn is a list, its length should match the number of outputs and labels"
            loss = sum(loss_fn[i](y_pred[i], y[i]) for i in range(len(loss_fn)))
        else:
            loss = sum([loss_fn(y_pred[i], y) for i in range(len(y_pred))])

        if isinstance(prunner, GradBasedPruner):
            loss.backward()
        return output_transform(x, y, y_pred, loss)

    return Engine(_update)
