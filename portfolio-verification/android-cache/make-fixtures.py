"""Build a staged album from the existing synthetic test photos."""

import argparse
import csv
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--count', type=int, required=True)
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--taken-at', type=datetime.fromisoformat, help='Device-local ISO date/time for EXIF DateTimeOriginal')
    args = parser.parse_args()
    if args.count < 1 or args.offset < 0 or args.offset + args.count > 99999:
        parser.error('unique fixture IDs must be in 00001–99999')
    files = sorted(args.source.glob('*/*.jpg'))
    if len(files) != 60:
        parser.error('expected the 60 existing synthetic JPEGs')
    reserved = ['f04_bibimbap_bowl', 'l08_mountain_autumn_trail', 'o07_hotel_room_key_card']
    targets = [next(p for p in files if p.stem == name) for name in reserved]
    pool = [p for p in files if p not in targets]
    args.output.mkdir(parents=True, exist_ok=False)
    with (args.output / 'manifest.csv').open('w', encoding='utf-8', newline='') as manifest:
        writer = csv.writer(manifest)
        writer.writerow(['fixture', 'synthetic_source', 'expected_query'])
        base_targets = {1: (targets[0], '그릇에 담긴 비빔밥'), 2: (targets[1], '가을 단풍이 든 산길')}
        for index in range(1, args.count + 1):
            number = args.offset + index
            source, query = pool[(number - 1) % len(pool)], ''
            if args.offset == 0 and index in base_targets:
                source, query = base_targets[index]
            elif args.offset > 0 and index == args.count:
                source, query = targets[2], '호텔 문을 여는 카드 키'
            prefix = 'EODIBENCH_NEW' if args.offset else 'EODIBENCH'
            name = f'{prefix}_{number:05}.jpg'
            with Image.open(source) as image:
                image = ImageOps.exif_transpose(image).convert('RGB')
                image = ImageOps.contain(image, (1280, 1280))
                if args.taken_at:
                    exif = Image.Exif()
                    stamp = args.taken_at.strftime('%Y:%m:%d %H:%M:%S')
                    exif[306] = stamp
                    capture = {36867: stamp, 36868: stamp}
                    if args.taken_at.utcoffset() is not None:
                        offset = args.taken_at.strftime('%z')
                        capture.update({36880: f'{offset[:3]}:{offset[3:]}', 36881: f'{offset[:3]}:{offset[3:]}'})
                    exif[34665] = capture
                    image.save(args.output / name, quality=90, exif=exif)
                else:
                    image.save(args.output / name, quality=90)
            writer.writerow([name, source.stem, query])


if __name__ == '__main__':
    main()
