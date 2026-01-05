#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute pixel diff metrics between two images.")
    parser.add_argument("--a", required=True, help="Path to image A")
    parser.add_argument("--b", required=True, help="Path to image B")
    parser.add_argument("--out", required=True, help="Path to output diff PNG")
    parser.add_argument("--report", required=True, help="Path to output JSON report")
    parser.add_argument(
        "--threshold",
        type=int,
        default=16,
        help="Pixel intensity threshold (0-255) for counting changed pixels (default: 16).",
    )
    parser.add_argument(
        "--crop",
        default=None,
        help="Optional crop box as 'left,top,right,bottom' in pixels for an additional focused metric.",
    )
    args = parser.parse_args()

    image_a = Image.open(args.a).convert("RGBA")
    image_b = Image.open(args.b).convert("RGBA")

    if image_a.size != image_b.size:
        target_size = (min(image_a.size[0], image_b.size[0]), min(image_a.size[1], image_b.size[1]))
        image_a = image_a.resize(target_size, Image.Resampling.LANCZOS)
        image_b = image_b.resize(target_size, Image.Resampling.LANCZOS)

    diff = ImageChops.difference(image_a, image_b)
    diff.save(args.out)

    diff_l = diff.convert("L")
    histogram = diff_l.histogram()

    total_pixels = diff_l.size[0] * diff_l.size[1]
    mean_abs = sum(i * count for i, count in enumerate(histogram)) / max(total_pixels, 1)
    changed_pixels = sum(histogram[args.threshold :])
    changed_ratio = changed_pixels / max(total_pixels, 1)

    report = {
        "image_a": str(Path(args.a)),
        "image_b": str(Path(args.b)),
        "size": {"width": diff_l.size[0], "height": diff_l.size[1]},
        "threshold": args.threshold,
        "mean_abs_diff": mean_abs,
        "changed_pixels": changed_pixels,
        "total_pixels": total_pixels,
        "changed_ratio": changed_ratio,
    }

    if args.crop:
        left_s, top_s, right_s, bottom_s = args.crop.split(",")
        crop_box = (int(left_s), int(top_s), int(right_s), int(bottom_s))
        crop = diff_l.crop(crop_box)
        crop_hist = crop.histogram()
        crop_total = crop.size[0] * crop.size[1]
        crop_mean_abs = sum(i * count for i, count in enumerate(crop_hist)) / max(crop_total, 1)
        crop_changed = sum(crop_hist[args.threshold :])
        report["crop"] = {
            "box": {"left": crop_box[0], "top": crop_box[1], "right": crop_box[2], "bottom": crop_box[3]},
            "size": {"width": crop.size[0], "height": crop.size[1]},
            "mean_abs_diff": crop_mean_abs,
            "changed_pixels": crop_changed,
            "total_pixels": crop_total,
            "changed_ratio": crop_changed / max(crop_total, 1),
        }

    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
