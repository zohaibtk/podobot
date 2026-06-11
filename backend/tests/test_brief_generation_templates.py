from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.types import BriefKind, ProfileKind
from app.modules.briefs.service import BriefService
from app.modules.episodes.models import Episode
from app.modules.outlines.models import OutlineVersion
from app.modules.profiles.models import Profile
from app.modules.series.models import Series


def test_host_and_guest_brief_templates_have_distinct_role_guidance() -> None:
    service = BriefService(cast(AsyncSession, None))
    series = Series(
        name="Leadership Unplugged",
        audience="Managers, Professionals",
        description="A series about candid leadership decisions.",
    )
    episode = Episode(
        episode_number=1,
        title="Beyond the Boardroom",
        premise="Explore how informal conversations reveal leadership signals.",
    )
    host = Profile(
        name="Elena Park",
        role_title="Editorial Strategy Host",
        kind=ProfileKind.HOST,
        archetype="Sharp editorial strategist",
        bio="Keeps executive conversations focused and practical.",
    )
    guest = Profile(
        name="Nadia Wallace",
        role_title="Venture Partner",
        kind=ProfileKind.GUEST,
        archetype="Venture operator and pattern reader",
    )
    outline_version = OutlineVersion(
        version_number=1,
        title="Generated outline: Beyond the Boardroom",
        outline_markdown=(
            "The episode should unpack candid conversations, hidden signals, "
            "and the decisions managers can make from informal leadership moments."
        ),
    )

    host_markdown = service._generated_brief_markdown(
        series=series,
        episode=episode,
        kind=BriefKind.HOST,
        profile=host,
        counterpart=guest,
        outline_version=outline_version,
    )
    guest_markdown = service._generated_brief_markdown(
        series=series,
        episode=episode,
        kind=BriefKind.GUEST,
        profile=guest,
        counterpart=host,
        outline_version=outline_version,
    )

    assert host_markdown != guest_markdown
    assert "### Host mission" in host_markdown
    assert "### Question flow" in host_markdown
    assert "### Handoff cues" in host_markdown
    assert "### Guest contribution" not in host_markdown
    assert "### Guest contribution" in guest_markdown
    assert "### Talking points to prepare" in guest_markdown
    assert "### Evidence and boundaries" in guest_markdown
    assert "### Question flow" not in guest_markdown
    assert "- Assigned host: Elena Park, Editorial Strategy Host" in host_markdown
    assert "- Assigned guest: Nadia Wallace, Venture Partner" in guest_markdown
