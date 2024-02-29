# -*- coding: utf-8 -*-
# @Time    : 10/23/23
# @Author  : Yaojie Shen
# @Project : MM-Video
# @File    : runner.py

import hydra
from hydra.utils import instantiate
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig, OmegaConf
from typing import *

import os
import shutil
from torch.nn import Module
from torch.utils.data import Dataset

import mm_video
from mm_video.trainer.trainer_utils import manual_seed
from mm_video.config import BaseConfig, runner_store
from mm_video.modeling.meter import Meter, DummyMeter
from mm_video.utils.profile import Timer

import logging

logger = logging.getLogger(__name__)

__all__ = ["Runner"]


@runner_store
class Runner:
    """
    Runner is a basic entry point for building datasets and models, and running the training, testing, and evaluation
    loop.

    """

    def __init__(self, dataset_splits: List[str] = ("train", "test", "eval")):
        self.dataset_splits = dataset_splits

    @staticmethod
    def build_dataset(dataset_config: DictConfig, dataset_splits: List[str]) -> Dict[str, Dataset]:
        def is_target(x: Any) -> bool:
            if isinstance(x, dict):
                return "_target_" in x
            if OmegaConf.is_dict(x):
                return "_target_" in x
            return False

        if is_target(dataset_config):
            with Timer("Building dataset from the configuration..."):
                dataset = {split: instantiate(dataset_config, split=split) for split in dataset_splits}
        elif (all(k in ("train", "test", "eval") for k in dataset_config.keys()) and
              all(is_target(v) or v is None for k, v in dataset_config.items())):
            # Allow selecting different dataset for train, test and eval
            # See https://stackoverflow.com/a/71371396 for the config syntax
            # Example:
            # ```
            # defaults:
            #   - /dataset@dataset.train: TrainSet
            #   - /dataset@dataset.test: TestSet
            # ```
            dataset = {k: instantiate(v) for k, v in dataset_config.items() if v is not None}
        else:
            raise ValueError(f"Dataset config is invalid: \n{OmegaConf.to_yaml(dataset_config)}")
        return dataset

    @staticmethod
    def build_model(model_builder_config: DictConfig) -> Module:
        with Timer("Building model from the configuration..."):
            model = instantiate(model_builder_config)
        return model

    @staticmethod
    def build_meter(meter_config: DictConfig) -> Meter:
        meter = instantiate(meter_config)
        if meter is None:
            logger.info("Meter is not specified.")
            meter = DummyMeter()
        return meter

    @staticmethod
    def save_code():
        mm_video_root = mm_video.__path__[0]
        assert os.path.exists(mm_video.__path__[0])
        shutil.make_archive(base_name=os.path.join(HydraConfig.get().runtime.output_dir, "code"), format="zip",
                            root_dir=os.path.dirname(mm_video_root), base_dir=os.path.basename(mm_video_root))

    def run(self, cfg: BaseConfig):
        if cfg.system.deterministic:
            manual_seed(cfg.system.seed)

        self.save_code()
        dataset = self.build_dataset(cfg.dataset, self.dataset_splits)
        model = self.build_model(cfg.model)
        meter = self.build_meter(cfg.meter)

        trainer = instantiate(cfg.trainer)(
            datasets=dataset,
            model=model,
            meter=meter
        )

        trainer.run()
