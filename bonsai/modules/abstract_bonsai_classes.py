from typing import Dict, Any
import torch
from torch import nn
import weakref


class BonsaiModule(nn.Module):

    def __init__(self, bonsai_model: nn.Module, module_cfg: Dict[str, Any]):
        super(BonsaiModule, self).__init__()
        self.bonsai_model = weakref.ref(bonsai_model)
        self.module_cfg = module_cfg

    def get_model(self):
        return self.bonsai_model()

    def forward(self, layer_input):
        raise NotImplementedError

    def calc_layer_output_size(self, input_size):
        raise NotImplementedError

    @staticmethod
    def prune_input(pruning_targets, module_name, module_tensor):
        raise NotImplementedError

    def propagate_pruning_target(self, initial_pruning_targets=None):
        raise NotImplementedError

    def prune_weights(self, output_pruning_targets=None, input_pruning_targets=None):
        weights = self.state_dict()
        for module_name, module_tensor in weights.items():
            if isinstance(self, Prunable):
                module_tensor = self.prune_output(output_pruning_targets, module_name, module_tensor)
            if input_pruning_targets:
                module_tensor = self.prune_input(input_pruning_targets, module_name, module_tensor)
            weights[module_name] = module_tensor
        return weights


class Prunable(BonsaiModule):
    """
    interface of prunable Bonsai modules
    """

    def __init__(self, bonsai_model: nn.Module, module_cfg: Dict[str, Any]):
        super().__init__(bonsai_model, module_cfg)
        self.weights = None
        self.activation = None
        self.grad = None
        if self.module_cfg.get("out_channels"):
            self.ranking = torch.zeros(self.module_cfg["out_channels"])
        elif self.module_cfg.get("out_features"):
            self.ranking = torch.zeros(self.module_cfg["out_features"])

    def forward(self, layer_input):
        raise NotImplementedError

    def reset(self):
        self.weights = None
        self.activation = None
        self.grad = None
        if self.module_cfg.get("out_channels"):
            self.ranking = torch.zeros(self.module_cfg["out_channels"])
        elif self.module_cfg.get("out_features"):
            self.ranking = torch.zeros(self.module_cfg["out_features"])

    def calc_layer_output_size(self, input_size):
        raise NotImplementedError

    def get_weights(self) -> torch.Tensor:
        """
        used to return weights with with output channels in the first dim. this is used for general implementation of
        ranking, and later each prunable module will handle the pruning based on the ranks regardless of his dim order
        :return: weights of prunabe module
        """
        raise NotImplementedError

    @staticmethod
    def prune_output(pruning_targets, module_name, module_tensor):
        raise NotImplementedError

    def propagate_pruning_target(self, initial_pruning_targets=None):
        raise NotImplementedError

    @staticmethod
    def prune_input(pruning_targets, module_name, module_tensor):
        raise NotImplementedError


class Elementwise(BonsaiModule):

    def __init__(self, bonsai_model: nn.Module, module_cfg: Dict[str, Any]):
        super().__init__(bonsai_model, module_cfg)

    def forward(self, layer_input):
        raise NotImplementedError

    def calc_layer_output_size(self, input_size):
        raise NotImplementedError

    @staticmethod
    def prune_input(pruning_targets, module_name, module_tensor):
        raise NotImplementedError

    def propagate_pruning_target(self, initial_pruning_targets=None):
        raise NotImplementedError
