# -*- coding: utf-8 -*-
# @Time    : 7/1/24
# @Author  : Yaojie Shen
# @Project : MM-Video
# @File    : runner.py

__all__ = ["Runner"]

from typing import Any

from omegaconf import DictConfig


class Runner:
    def run(
            self, cfg: DictConfig, **kwargs: Any
    ) -> None:
        """
        Main entry point for running the application, define the main logic here.
        For each application, a runner will be instantiated from the runner config, and the global config will be
        passed for building the application.

        :param cfg: Global config
        :return:
        """
        ...
