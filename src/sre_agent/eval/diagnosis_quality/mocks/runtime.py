"""Runtime state for diagnosis quality mocked tools."""

from dataclasses import dataclass

from sre_agent.eval.diagnosis_quality.dataset.schema import DiagnosisQualityEvalCase


@dataclass
class MockToolRuntime:
    """Runtime state for one eval case."""

    case: DiagnosisQualityEvalCase
