"""Render public evidence cards from recorded outputs, without source photos."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONT = Path('C:/Windows/Fonts/malgun.ttf')
BOLD = Path('C:/Windows/Fonts/malgunbd.ttf')


def evidence(filename, title, subtitle, panels, accent):
    canvas = Image.new('RGB', (1180, 620), '#eef2f7')
    draw = ImageDraw.Draw(canvas)

    def put(x, y, text, size, color='#172334', bold=False):
        font = ImageFont.truetype(str(BOLD if bold else FONT), size)
        draw.text((x, y), text, font=font, fill=color, spacing=7)

    draw.rounded_rectangle((26, 24, 1154, 596), 22, fill='#ffffff')
    put(56, 51, title, 36, accent, True)
    put(56, 111, subtitle, 19)
    for i, (heading, body) in enumerate(panels):
        top = 164 + i * 123
        draw.rounded_rectangle((56, top, 1124, top + 108), 13, fill='#f1f5f9')
        put(76, top + 12, heading, 19, accent, True)
        put(76, top + 43, body, 19)
    put(56, 555, '2026-11-25  |  592d2351  |  사진과 개인정보 없이 실제 실행 기록에서 생성', 16)
    canvas.save(HERE / filename)


api = json.loads((HERE / 'photo-results.json').read_text(encoding='utf-8'))
onnx = json.loads((HERE / 'onnx-results.json').read_text(encoding='utf-8'))
good = next(row for row in onnx['search'] if row['expected'] == ['f04'])
bad = next(row for row in onnx['search'] if row['current']['top5'] == ['f09'])
valid, invalid = (item['output'] for item in api['warmDemo'])
evidence('normal-result.png', '정상  |  비빔밥 사진 찾기', '공개 앱의 검색 로직 + 실제 ONNX 가중치 · 데스크톱 재현', [
    ('입력', f'“{good["query"]}”  ·  로컬 합성 여행 사진 60장'),
    ('처리', 'SigLIP2 이미지·문장 임베딩 → 내적 순위 → 1위 점수 대비 75% 필터'),
    ('출력', f'1위 {good["current"]["top5"][0]} · 정답 JPEG 열기 성공 · {good["desktopHarnessMs"]:.1f} ms\n'
           f'서버 분류 확인  |  {valid["photoId"]} → {valid["topics"][0]} · {valid["status"]}'),
], '#076655')
evidence('failure-result.png', '실패  |  정답 없는 질문에 사진 반환', '공개 앱의 검색 로직 + 실제 ONNX 가중치 · 데스크톱 재현', [
    ('입력', f'“{bad["query"]}”  ·  정답 사진 0장'),
    ('검색 출력', f'{bad["current"]["top5"][0]} (해산물 시장)  ·  결과 {bad["current"]["count"]}장  ·  {bad["desktopHarnessMs"]:.1f} ms\n'
               '상대 점수 필터는 최상위 오답을 유지했다.'),
    ('별도 서버 실패 경로', f'손상 JPEG {invalid["photoId"]} → {invalid["status"]} / {invalid["errorCode"]}\n'
                      '같은 요청의 정상 사진 처리 결과는 유지됐다.'),
], '#a9472b')
