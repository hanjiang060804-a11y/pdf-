from pdf_tra.core.models import PipelineContext
from pdf_tra.pipeline.registry import resolve_steps


def run_pipeline(ctx: PipelineContext, step_names: list[str]) -> PipelineContext:
    steps = resolve_steps(step_names)
    for step in steps:
        if step.should_run(ctx):
            step.run(ctx)
    return ctx
