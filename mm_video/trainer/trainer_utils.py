# -*- coding: utf-8 -*-
# @Time    : 2023/12/15
# @Author  : Yaojie Shen
# @Project : MM-Video
# @File    : trainer_utils.py

import os
import torch
from torch import nn
import torch.distributed as dist
import random
import numpy as np
from typing import *
import logging

logger = logging.getLogger(__name__)

__all__ = ["barrier", "get_module_class_from_name", "unwrap_model", "load_state_dict", "save_state_dict", "manual_seed",
           "get_write_freq"]


def barrier(debug_msg: Optional[str] = None, disabled: bool = False):
    """
    A util for calling distributed barrier.

    :param debug_msg: Write message to debug log
    :param disabled: Disable barrier
    """
    if dist.is_initialized() and not disabled:
        if debug_msg is not None:
            logger.debug("Reached the '%s' barrier, waiting for other processes.", debug_msg)
        dist.barrier()
        if debug_msg is not None:
            logger.debug("Exited the '%s' barrier.", debug_msg)


def get_module_class_from_name(module, name):
    """
    Gets a class from a module by its name.

    Args:
        module (`torch.nn.Module`): The module to get the class from.
        name (`str`): The name of the class.
    """
    modules_children = list(module.children())
    if module.__class__.__name__ == name:
        return module.__class__
    elif len(modules_children) == 0:
        return
    else:
        for child_module in modules_children:
            module_class = get_module_class_from_name(child_module, name)
            if module_class is not None:
                return module_class


def unwrap_model(model: nn.Module) -> nn.Module:
    """
    Recursively unwraps a model from potential containers (as used in distributed training).

    Args:
        model (`torch.nn.Module`): The model to unwrap.
    """
    # since there could be multiple levels of wrapping, unwrap recursively
    if hasattr(model, "module"):
        return unwrap_model(model.module)
    else:
        return model


def load_state_dict(model: nn.Module, model_file: str, strict: bool = False):
    state_dict = torch.load(model_file, map_location="cpu")
    incompatible_keys = model.load_state_dict(state_dict, strict=strict)

    if len(incompatible_keys.missing_keys) > 0:
        logger.warning("Weights of {} not initialized from pretrained model: {}"
                       .format(model.__class__.__name__, "\n   " + "\n   ".join(incompatible_keys.missing_keys)))
    if len(incompatible_keys.unexpected_keys) > 0:
        logger.warning("Weights from pretrained model not used in {}: {}"
                       .format(model.__class__.__name__, "\n   " + "\n   ".join(incompatible_keys.unexpected_keys)))

    if len(incompatible_keys.missing_keys) == 0 and len(incompatible_keys.unexpected_keys) == 0:
        logger.info("All keys loaded successfully for {}".format(model.__class__.__name__))


def save_state_dict(model: nn.Module, model_file: str):
    state_dict = model.state_dict()
    os.makedirs(os.path.dirname(model_file), exist_ok=True)
    torch.save(state_dict, model_file)


def manual_seed(seed):
    torch.manual_seed(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.cuda.manual_seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = True
    logger.info("Manual seed is set to %s", seed)


def get_write_freq(x: Optional[int]):
    """
    Returns the frequency value for writing data.

    If the input `x` is None, it implies an infinite frequency, the function returns `float('inf')`.
    Otherwise, it returns the unchanged input value.
    """
    assert x is None or type(x) is int
    return float("inf") if x is None else x
