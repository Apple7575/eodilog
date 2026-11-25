"""Run the published photo API on local fixtures; export IDs and outputs only."""

import json
import logging
import sys
from pathlib import Path
from time import perf_counter

from fastapi.testclient import TestClient


def main():
    source, fixtures, output = map(Path, sys.argv[1:])
    sys.path.insert(0, str(source.resolve()))
    from app.core.config import Settings
    from app.main import create_app

    logging.basicConfig(level=logging.INFO)
    app = create_app(Settings(_env_file=None, internal_api_token="portfolio-local", request_budget_seconds=90))
    classifier = app.state.photo_classifier
    assert classifier._head is not None and classifier._embedder._visual_weights
    cases = [(p.stem.split('_')[0] + ('-b' if p.stem.endswith('_b') else '-a' if p.stem.endswith('_a') else ''), p.parent.name, p.read_bytes())
             for p in sorted(fixtures.glob('*/*.jpg'))]
    assert len(cases) == 60 and len({case[0] for case in cases}) == 60
    results = []
    timing = []
    with TestClient(app) as client:
        def post(batch, run):
            ids = [case[0] for case in batch]
            files = [('files', (f'{i}.jpg', payload, 'image/jpeg')) for i, _, payload in batch]
            start = perf_counter()
            reply = client.post('/ai/v1/photo-classifications', files=files,
                                data={'meta': json.dumps({'photoIds': ids})},
                                headers={'X-Internal-Token': 'portfolio-local'})
            elapsed = round((perf_counter() - start) * 1000, 1)
            reply.raise_for_status()
            rows = reply.json()['data']['photos']
            assert [row['photoId'] for row in rows] == ids
            for row in rows:
                if row['groupId'] is not None:
                    row['groupId'] = f'group-{next(i for i, item in enumerate(rows) if item["groupId"] == row["groupId"])}'
            timing.append({'run': run, 'items': len(batch), 'httpStatus': reply.status_code, 'ms': elapsed})
            return [{'expected': expected, 'output': row} for (_, expected, _), row in zip(batch, rows, strict=True)]

        first_food = next(case for case in cases if case[0] == 'f01')
        demo = post([first_food, ('bad-01', 'INVALID_IMAGE', b'not a jpeg')], 'cold mixed request')
        for index in range(0, len(cases), 8):
            results.extend(post(cases[index:index+8], f'batch {index // 8 + 1}'))
        warm = post([first_food, ('bad-01', 'INVALID_IMAGE', b'not a jpeg')], 'warm mixed request')
    output.write_text(json.dumps({'source': '592d2351', 'cases': results, 'demo': demo, 'warmDemo': warm, 'timings': timing}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
