from pathlib import Path

from app.services.policy_agent.cip_loader import CIPDataset, CIPNotFoundError


DATASET_PATH = Path('data/policy/cip_codes.json')


def test_cip_loader_returns_entry_for_known_code():
    dataset = CIPDataset.load(DATASET_PATH)

    entry = dataset.get('11.0701')

    assert entry.cip_code == '11.0701'
    assert entry.title
    assert entry.description


def test_cip_loader_raises_for_unknown_code():
    dataset = CIPDataset.load(DATASET_PATH)

    try:
        dataset.get('99.9999')
    except CIPNotFoundError as exc:
        assert '99.9999' in str(exc)
    else:
        raise AssertionError('Expected CIPNotFoundError for unknown code')
