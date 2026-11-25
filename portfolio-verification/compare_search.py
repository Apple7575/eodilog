"""Compare original webli B-32 and exact phone ONNX. Export safe synthetic IDs only."""

import csv
import io
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import onnxruntime as ort
import open_clip
import torch
from PIL import Image, ImageOps

from run_onnx_eval import QUESTIONS

CALIBRATION = {
    '검은 밤에 불이 켜진 다리': ['l02'], '커피 위에 그린 라떼아트': ['f06'],
    '기차를 타는 데 쓰는 승차권': ['o02'], '노란 잠수함 내부 조종석': [],
    '스키 점프대에서 뛰는 선수': [], '사막의 낙타 행렬': [],
}
HOLDOUT = {
    '가을 단풍이 든 산길': ['l08'], '철판 위에서 고기를 굽는 장면': ['f03'],
    '궁궐에서 한복을 입은 사람': ['p04'], '호텔 문을 여는 카드 키': ['o07'],
    '비 오는 길에서 우산을 쓰고 걷는 사람들': ['l09'], '나란히 놓인 빵이 담긴 쟁반': ['f08'],
    '새하얀 눈밭을 달리는 개썰매': [], '놀이공원에서 도는 대관람차': [],
    '피아노를 연주하는 손': [], '폭포 밑을 지나는 카약': [],
    '아쿠아리움의 투명한 해파리': [], '축구장 골대 앞의 골키퍼': [],
}


def encode_phone(models, questions):
    with TemporaryDirectory() as directory:
        path = Path(directory)
        (path / 'tokenizer.ts').write_bytes(subprocess.check_output([
            'git', 'show', '592d2351:frontend/src/features/ondevice/siglip-tokenizer.ts']))
        (path / 'query.mts').write_text('''import { readFileSync } from 'node:fs';
import { SiglipTokenizer } from './tokenizer.ts';
const tokenizer = new SiglipTokenizer(JSON.parse(readFileSync(process.argv[2], 'utf8')));
console.log(JSON.stringify(JSON.parse(readFileSync(0, 'utf8')).map(q => tokenizer.encode(q))));
''', encoding='utf-8')
        args = ['node', str(path / 'query.mts'), str(models / 'tokenizer.json')]
        return np.asarray(json.loads(subprocess.check_output(args, input=json.dumps(questions).encode())), dtype=np.int32)


def pixels(image):
    return ((np.asarray(image, dtype=np.float32) / 255 - .5) / .5).transpose(2, 0, 1)


def load_fixture(path):
    with Image.open(path) as raw:
        image = ImageOps.exif_transpose(raw).convert('RGB')
    w, h = image.size
    w, h = round(w * 256 / min(w, h)), round(h * 256 / min(w, h))
    image = image.resize((w, h), Image.Resampling.BICUBIC)
    x, y = (w - 256) // 2, (h - 256) // 2
    encoded = io.BytesIO()
    image.crop((x, y, x + 256, y + 256)).save(encoded, format='JPEG', quality=100)
    with Image.open(encoded) as decoded:
        return pixels(decoded)


def tag(path):
    return path.stem.split('_')[0] + (f'-{path.stem[-1]}' if path.stem.endswith(('_a', '_b')) else '')


def main():
    models, source, output = map(Path, sys.argv[1:4])
    historical = len(sys.argv) > 4
    if historical:
        images = np.load(source / 'evaldata/eval256.npz')
        captions = json.loads((source / 'evaldata/cap_eval.json').read_text(encoding='utf-8'))
        files = list(images['files'])
        stored = json.loads((source / 'final/eval_files.json').read_text(encoding='utf-8'))['files']
        assert files == stored
        keep = [i for i, key in enumerate(files) if key in captions]
        raw = images['x'][keep]
        data = np.asarray([pixels(photo) for photo in raw])
        ids = [f'h{i + 1:04}' for i in range(len(keep))]
        specs = [('historical_grounded', captions[files[i]]['query'], [key]) for i, key in zip(keep, ids, strict=True)]
    else:
        fixtures = sorted(source.glob('*/*.jpg'))
        data = np.asarray([load_fixture(photo) for photo in fixtures])
        ids = [tag(photo) for photo in fixtures]
        assert len(ids) == len(set(ids)) == 60
        specs = [(split, query, expected) for split, queries in
                 [('regression', QUESTIONS), ('calibration', CALIBRATION), ('holdout', HOLDOUT)]
                 for query, expected in queries.items()]
    assert all(set(expected) <= set(ids) for _, _, expected in specs)
    questions = [q for _, q, _ in specs]
    torch.set_num_threads(4)
    baseline, _, _ = open_clip.create_model_and_transforms('ViT-B-32-SigLIP2-256', pretrained='webli')
    baseline.eval()
    tokenizer = open_clip.get_tokenizer('ViT-B-32-SigLIP2-256')
    with torch.inference_mode():
        bi = np.concatenate([baseline.encode_image(torch.from_numpy(data[i:i+16])).numpy() for i in range(0, len(data), 16)])
        bt = np.concatenate([baseline.encode_text(tokenizer(questions[i:i+32])).numpy() for i in range(0, len(questions), 32)])
    del baseline
    print('baseline embeddings ready', len(ids), len(questions), flush=True)
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    options.log_severity_level = 3
    def session(file):
        return ort.InferenceSession(str(models / file), options, providers=['CPUExecutionProvider'])
    visual = session('photo_image_int8.onnx')
    text = session('photo_text_w4_i32.onnx')
    pi = np.concatenate([visual.run(['features'], {'pixels': data[i:i+16].copy()})[0] for i in range(0, len(data), 16)])
    tokens = encode_phone(models, questions)
    pt = np.concatenate([text.run(['embedding'], {'ids32': tokens[i:i+16]})[0] for i in range(0, len(tokens), 16)])
    def norm(v):
        return v / np.linalg.norm(v, axis=1, keepdims=True)
    old, phone = norm(bt) @ norm(bi).T, norm(pt) @ norm(pi).T
    rows = []
    for i, (split, query, expected) in enumerate(specs):
        row = {'query_id': f'q{i+1:04}', 'split': split, 'query': '' if historical else query,
               'expected_ids': '|'.join(expected), 'has_answer': bool(expected)}
        for name, matrix in [('webli', old), ('phone', phone)]:
            index = np.argsort(-matrix[i], kind='stable')
            top = [ids[j] for j in index[:5]]
            row[f'{name}_top5'] = '|'.join(top)
            row[f'{name}_top1'] = top[0]
            row[f'{name}_score'] = float(matrix[i, index[0]])
            row[f'{name}_hit1'] = top[0] in expected if expected else ''
            row[f'{name}_rank'] = next((k for k, j in enumerate(index, 1) if ids[j] in expected), '')
        row['hit_changed'] = row['webli_hit1'] != row['phone_hit1'] if expected else ''
        rows.append(row)
    if not historical:
        cal = [r for r in rows if r['split'] == 'calibration']
        scores = sorted(set(r['phone_score'] for r in cal))
        cuts = [scores[0] - 1, *(float((a+b)/2) for a, b in zip(scores, scores[1:])), scores[-1] + 1]
        def errors(cut):
            return sum((r['phone_score'] < cut) == r['has_answer'] for r in cal)
        cut = min(cuts, key=lambda value: (errors(value), -value))
        for row in rows:
            row['phone_abstain'] = row['phone_score'] < cut
            row['calibration_cut'] = cut
    with output.open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    main()
