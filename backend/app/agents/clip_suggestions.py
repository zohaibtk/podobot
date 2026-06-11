import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from app.agents.llm.gemini import GeminiLLMProvider
from app.modules.episodes.models import Episode
from app.modules.narratives.models import Narrative
from app.modules.research.models import ResearchDocument
from app.modules.research_sources.models import ResearchSource
from app.modules.series.models import Series


class ClipSuggestionProvider(Protocol):
    async def generate_json(self, prompt: str) -> dict[str, object]:
        ...


@dataclass(frozen=True)
class EvidenceSignal:
    source_name: str
    provider_type: str
    title: str
    summary: str
    composite_score: int
    confidence_level: str
    trend_score: int | None
    trend_available: bool


@dataclass(frozen=True)
class ClipSuggestionDraft:
    slot_number: int
    title: str
    rationale: str
    start_timecode: str
    end_timecode: str


class ClipSuggestionAgent:
    agent_key = "clip_suggestion"
    prompt_key = "clip_suggestion.v1"

    def __init__(self, provider: ClipSuggestionProvider | None = None) -> None:
        self.provider = provider or GeminiLLMProvider()

    async def suggest(
        self,
        *,
        series: Series,
        episode: Episode,
        transcript_text: str,
        narrative: Narrative | None,
        evidence_signals: list[EvidenceSignal],
    ) -> list[ClipSuggestionDraft]:
        response = await self.provider.generate_json(
            self._prompt(
                series=series,
                episode=episode,
                transcript_text=transcript_text,
                narrative=narrative,
                evidence_signals=evidence_signals,
            )
        )
        return self._validated_clips(response)

    def _prompt(
        self,
        *,
        series: Series,
        episode: Episode,
        transcript_text: str,
        narrative: Narrative | None,
        evidence_signals: list[EvidenceSignal],
    ) -> str:
        context = {
            "series": {
                "name": series.name,
                "audience": series.audience,
                "description": series.description,
            },
            "episode": {
                "number": episode.episode_number,
                "title": episode.title,
                "premise": episode.premise,
            },
            "selected_narrative": self._narrative_payload(narrative),
            "research_and_trend_signals": [
                self._evidence_payload(signal) for signal in evidence_signals[:8]
            ],
            "transcript": self._compact_transcript(transcript_text),
        }
        return (
            "You are PodoBot's Clip Suggestion Agent. Suggest exactly three "
            "metadata-only short clip moments from the uploaded transcript.\n\n"
            "Important rules:\n"
            "- Use the transcript as the source of timecoded moments.\n"
            "- Use selected_narrative and research_and_trend_signals to decide which "
            "moments are most relevant, high-confidence, and timely.\n"
            "- Prefer moments that connect the episode conversation to strong source "
            "evidence or trend signals.\n"
            "- Do not auto-extract media and do not claim a clip file exists.\n"
            "- start_timecode and end_timecode must be HH:MM:SS.\n"
            "- Return JSON only with this exact shape: "
            '{"clips":[{"slot_number":1,"title":"...","rationale":"...",'
            '"start_timecode":"00:00:00","end_timecode":"00:00:30"}]}.\n\n'
            f"Context JSON:\n{json.dumps(context, default=self._json_default)}"
        )

    def _validated_clips(self, response: dict[str, object]) -> list[ClipSuggestionDraft]:
        raw_clips = response.get("clips")
        if not isinstance(raw_clips, list):
            raw_clips = response.get("suggestions")
        if not isinstance(raw_clips, list):
            raise ValueError("Gemini did not return clip suggestions.")

        drafts: list[ClipSuggestionDraft] = []
        seen_slots: set[int] = set()
        for item in raw_clips:
            if not isinstance(item, dict):
                continue
            slot_number = self._slot_number(item.get("slot_number"))
            if slot_number is None or slot_number in seen_slots:
                continue
            title = self._clean_text(item.get("title"), max_length=220)
            rationale = self._clean_text(item.get("rationale"), max_length=1200)
            start_timecode = self._timecode(item.get("start_timecode"))
            end_timecode = self._timecode(item.get("end_timecode"))
            if not title or not rationale or not start_timecode or not end_timecode:
                continue
            drafts.append(
                ClipSuggestionDraft(
                    slot_number=slot_number,
                    title=title,
                    rationale=rationale,
                    start_timecode=start_timecode,
                    end_timecode=end_timecode,
                )
            )
            seen_slots.add(slot_number)

        if len(drafts) != 3:
            raise ValueError("Gemini did not return exactly three usable clip suggestions.")
        return sorted(drafts, key=lambda draft: draft.slot_number)

    def _narrative_payload(self, narrative: Narrative | None) -> dict[str, object] | None:
        if narrative is None:
            return None
        return {
            "title": narrative.title,
            "thesis": narrative.thesis,
            "summary": narrative.summary,
            "confidence_score": narrative.confidence_score,
            "supporting_signals": narrative.supporting_signals,
        }

    def _evidence_payload(self, signal: EvidenceSignal) -> dict[str, object]:
        return {
            "source_name": signal.source_name,
            "provider_type": signal.provider_type,
            "title": signal.title,
            "summary": signal.summary,
            "composite_score": signal.composite_score,
            "confidence_level": signal.confidence_level,
            "trend_score": signal.trend_score,
            "trend_available": signal.trend_available,
        }

    def _compact_transcript(self, transcript_text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", transcript_text.strip())
        return text[:8000]

    def _slot_number(self, value: object) -> int | None:
        try:
            slot_number = int(str(value))
        except (TypeError, ValueError):
            return None
        return slot_number if 1 <= slot_number <= 3 else None

    def _timecode(self, value: object) -> str | None:
        match = re.search(r"(?:(\d{1,2}):)?(\d{2}):(\d{2})", str(value or ""))
        if not match:
            return None
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _clean_text(self, value: object, *, max_length: int) -> str:
        text = str(value or "").strip()
        text = re.sub(r"\s+", " ", text)
        return text[:max_length].strip()

    def _json_default(self, value: Any) -> str:
        return str(value)


def evidence_signal_from_document(
    document: ResearchDocument,
    source: ResearchSource,
) -> EvidenceSignal:
    return EvidenceSignal(
        source_name=source.name,
        provider_type=str(source.provider_type),
        title=document.title,
        summary=document.content_excerpt or document.normalized_content or "",
        composite_score=int(document.composite_score or 0),
        confidence_level=str(document.confidence_level),
        trend_score=document.trend_score,
        trend_available=bool(document.trend_available),
    )
