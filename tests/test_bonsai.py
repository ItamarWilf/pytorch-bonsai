from torch import nn, optim
from bonsai import Bonsai
from pruning.bonsai_prunners import WeightL2Prunner, ActivationL2Prunner, TaylorExpansionPrunner
from torchvision.datasets import CIFAR10
from torchvision.transforms import ToTensor
from torch.utils.data import DataLoader, sampler
import pytest

NUM_TRAIN = 2000
NUM_VAL = 1000


@pytest.fixture()
def train_dl():
    cifar10_train = CIFAR10('.datasets/CIfAR10', train=True, download=True, transform=ToTensor())
    yield DataLoader(cifar10_train, batch_size=64, sampler=sampler.SubsetRandomSampler(range(NUM_TRAIN)))


@pytest.fixture()
def val_dl():
    cifar10_val = CIFAR10('.datasets/CIfAR10', train=True, download=True, transform=ToTensor())
    yield DataLoader(cifar10_val, batch_size=64,
                     sampler=sampler.SubsetRandomSampler(range(NUM_TRAIN, NUM_TRAIN + NUM_VAL)))


@pytest.fixture()
def test_dl():
    cifar10_test = CIFAR10('.datasets/CIfAR10', train=False, download=True, transform=ToTensor())
    yield DataLoader(cifar10_test, batch_size=64)


@pytest.fixture()
def bonsai_blank():
    cfg_path = "model_cfgs_for_tests/FCN-VGG16.cfg"
    bonsai = Bonsai(cfg_path)
    yield bonsai


@pytest.fixture()
def optimizer(bonsai_blank):
    adam = optim.Adam(bonsai_blank.model.parameters(), lr=1e-3)
    yield adam


@pytest.fixture()
def criterion():
    yield nn.CrossEntropyLoss()


def test_build_bonsai_with_no_prunner():
    cfg_path = "model_cfgs_for_tests/U-NET.cfg"
    _ = Bonsai(cfg_path)


def test_build_bonsai_with_weight_prunner():
    cfg_path = "model_cfgs_for_tests/U-NET.cfg"
    _ = Bonsai(cfg_path, WeightL2Prunner)


def test_bonsai_rank_method_with_weight_prunner():
    cfg_path = "model_cfgs_for_tests/U-NET.cfg"
    bonsai = Bonsai(cfg_path, WeightL2Prunner)
    bonsai.rank(None, None)


class TestBonsaiFinetune:

    def test_bonsai_finetune(self, bonsai_blank, train_dl, optimizer, criterion):
        bonsai_blank.finetune(train_dl, optimizer, criterion, max_epochs=1)


# download cifar10 val and test...
class TestBonsaiRank:

    def test_bonsai_rank_method_with_activation_prunner(self, val_dl, criterion):
        cfg_path = "model_cfgs_for_tests/FCN-VGG16.cfg"
        bonsai = Bonsai(cfg_path, ActivationL2Prunner)
        bonsai.rank(val_dl, criterion)

    def test_bonsai_rank_method_with_gradient_prunner(self, val_dl, criterion):
        cfg_path = "model_cfgs_for_tests/FCN-VGG16.cfg"
        bonsai = Bonsai(cfg_path, TaylorExpansionPrunner, normalize=True)
        bonsai.rank(val_dl, criterion)
        print("well")


class TestWriteRecipe:

    def test_write_recipe(self, val_dl):
        cfg_path = "model_cfgs_for_tests/FCN-VGG16.cfg"
        bonsai = Bonsai(cfg_path, WeightL2Prunner, normalize=True)
        bonsai.rank(val_dl, None)
        init_pruning_targets = bonsai.prunner.get_prunning_plan(99)
        bonsai.write_pruned_recipe("testing.cfg", init_pruning_targets)
        print("well")


class TestFullPrune:

    def test_run_pruning(self, train_dl, val_dl, test_dl, criterion, optimizer):
        cfg_path = "model_cfgs_for_tests/FCN-VGG16.cfg"
        bonsai = Bonsai(cfg_path, TaylorExpansionPrunner, normalize=True)

        bonsai.run_pruning_loop(train_dl=train_dl, eval_dl=val_dl, optimizer=optimizer, criterion=criterion)
