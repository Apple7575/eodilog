"""Run local copies of the Android model files with desktop ONNX Runtime."""

import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

QUESTIONS = {
    '바다 위로 지는 해': ['l11-a', 'l11-b'],
    '그릇에 담긴 비빔밥': ['f04'],
    '벚꽃이 늘어선 길': ['l12-a', 'l12-b'],
    '가격이 적힌 식당 메뉴판': ['o04', 'o13'],
    '눈 위의 북극곰': [],
    '수중에서 헤엄치는 고래': [],
    '발사대에서 이륙하는 우주 로켓': [],
    '에펠탑 앞에 세워진 빨간 소방차': [],
}
SIZES = {'photo_image_int8.onnx': 102925949, 'photo_text_w4_i32.onnx': 97350690,
         'head.json': 65983, 'tokenizer.json': 1220249}


def norm(row):
    return row / np.linalg.norm(row)


def main():
    models, photos, output = map(Path, sys.argv[1:])
    integrity = {}
    for name, size in SIZES.items():
        assert (models / name).stat().st_size == size
        with (models / name).open('rb') as file:
            integrity[name] = {'bytes': size, 'sha256': hashlib.file_digest(file, 'sha256').hexdigest()}
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    options.log_severity_level = 3
    providers = ['CPUExecutionProvider']
    start = perf_counter()
    vision = ort.InferenceSession(str(models / 'photo_image_int8.onnx'), options, providers=providers)
    text = ort.InferenceSession(str(models / 'photo_text_w4_i32.onnx'), options, providers=providers)
    load_ms = (perf_counter() - start) * 1000
    head = json.loads((models / 'head.json').read_text(encoding='utf-8'))
    weight, bias = np.asarray(head['W']), np.asarray(head['B'])
    entries, classification, fixture_paths = [], [], {}
    for path in sorted(photos.glob('*/*.jpg')):
        start = perf_counter()
        with Image.open(path) as raw:
            image = ImageOps.exif_transpose(raw).convert('RGB')
        w, h = image.size
        w, h = round(w * 256 / min(w, h)), round(h * 256 / min(w, h))
        image = image.resize((w, h), Image.Resampling.BICUBIC)
        x, y = (w - 256) // 2, (h - 256) // 2
        encoded = io.BytesIO()
        image.crop((x, y, x + 256, y + 256)).save(encoded, format='JPEG', quality=100)
        pixels = ((np.asarray(Image.open(encoded), dtype=np.float32) / 255 - .5) / .5).transpose(2, 0, 1)[None].copy()
        vector = norm(vision.run(['features'], {'pixels': pixels})[0][0])
        scores = (weight @ vector + bias) * head['scale']
        tag = path.stem.split('_')[0] + ('-b' if path.stem.endswith('_b') else '-a' if path.stem.endswith('_a') else '')
        fixture_paths[tag] = path
        entries.append({'id': tag, 'f': vector.tolist()})
        classification.append({'id': tag, 'expected': path.parent.name, 'predicted': head['topics'][int(scores.argmax())],
                               'ms': round((perf_counter() - start) * 1000, 2)})
    assert len(entries) == len(fixture_paths) == 60

    with TemporaryDirectory() as directory:
        temp = Path(directory)
        for filename in ('search-rules.ts', 'siglip-tokenizer.ts'):
            blob = subprocess.check_output(['git', 'show', f'592d2351:frontend/src/features/ondevice/{filename}'])
            (temp / filename).write_bytes(blob)
        script = temp / 'query.mts'
        script.write_text('''import { readFileSync } from 'node:fs';
import { rankBySimilarity, relevantOnly } from './search-rules.ts';
import { SiglipTokenizer } from './siglip-tokenizer.ts';
const [stage, spec] = process.argv.slice(2);
const data = JSON.parse(readFileSync(0, 'utf8'));
const start = performance.now();
const result = stage === 'tokenize'
  ? new SiglipTokenizer(JSON.parse(readFileSync(spec, 'utf8'))).encode(data)
  : (() => { const ranked = rankBySimilarity(data.vector, data.entries, 60);
              return { unfiltered: ranked, current: relevantOnly(ranked, 0.75) }; })();
console.log(JSON.stringify({ result, ms: performance.now() - start }));
''', encoding='utf-8')

        def node(stage, value):
            return json.loads(subprocess.check_output(['node', str(script), stage, str((models / 'tokenizer.json').resolve())],
                                                      input=json.dumps(value).encode()))

        search = []
        for question, expected in QUESTIONS.items():
            start = perf_counter()
            encoded = node('tokenize', question)
            infer = perf_counter()
            vector = norm(text.run(['embedding'], {'ids32': np.asarray([encoded['result']], dtype=np.int32)})[0][0])
            infer_ms = (perf_counter() - infer) * 1000
            ranked = node('rank', {'vector': vector.tolist(), 'entries': entries})
            total = (perf_counter() - start) * 1000
            row = {'query': question, 'expected': expected, 'desktopHarnessMs': round(total, 1),
                   'processingMs': round(encoded['ms'] + infer_ms + ranked['ms'], 1)}
            for name, ranks in ranked['result'].items():
                ranks = [item['id'] for item in ranks]
                hit_ids = [key for key in ranks if key in expected]
                opened = []
                for key in hit_ids:
                    with Image.open(fixture_paths[key]) as photo:
                        photo.load()
                    opened.append(key)
                row[name] = {'count': len(ranks), 'top5': ranks[:5], 'opened': opened,
                             'firstCorrectRank': ranks.index(hit_ids[0]) + 1 if hit_ids else None,
                             'unsupportedOnNegative': not expected and bool(ranks)}
            search.append(row)
    output.write_text(json.dumps({'source': '592d2351', 'ort': ort.__version__, 'files': integrity,
                                  'loadMs': round(load_ms, 1), 'classification': classification, 'search': search},
                                 ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
