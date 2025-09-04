# test(config): ensure parse_limits supports alias forms and errors on bad specs

import pytest

from inspect_agents.config import parse_limits


def test_parse_limits_aliases_ok():
    limits = parse_limits([
        {"type": "time", "seconds": 1.5},
        {"type": "messages", "max": 8},
        {"type": "tokens", "limit": 6000},
    ])
    # We don't assert concrete types (opaque Inspect objects), just count
    assert isinstance(limits, list) and len(limits) == 3


@pytest.mark.parametrize(
    "bad",
    [
        {"type": "foo", "value": 1},
        {"type": "time", "value": "NaN"},
        {"type": "tokens", "value": 3.14},
    ],
)
def test_parse_limits_errors(bad):
    with pytest.raises(ValueError):
        parse_limits([bad])

