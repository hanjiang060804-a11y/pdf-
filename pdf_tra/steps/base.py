from abc import ABC, abstractmethod

from pdf_tra.core.models import PipelineContext


class Step(ABC):
    name: str
    required: bool = True

    @abstractmethod
    def should_run(self, ctx: PipelineContext) -> bool:
        raise NotImplementedError

    @abstractmethod
    def run(self, ctx: PipelineContext) -> None:
        raise NotImplementedError
