"""Build the recruiter-facing animated pipeline walkthrough from screenshots."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCREENSHOTS = PROJECT_ROOT / "docs" / "screenshots"
OUTPUT = PROJECT_ROOT / "docs" / "demo" / "telecom-pipeline-demo.gif"
CANVAS_SIZE = (960, 620)
IMAGE_AREA = (960, 540)

SCENES = [
    ("airflow-successful-dag-run.png", "1. Airflow orchestrates all five pipeline tasks", 10_000),
    ("databricks-contract-kpis.png", "2. Databricks serves contract-level Gold metrics", 10_000),
    ("databricks-payment-kpis.png", "3. Databricks exposes payment-method churn drivers", 10_000),
    ("godrisoft-insights-churn.png", "4. Godrisoft Insights answers from governed data", 10_000),
    ("slack-telecom-insights.png", "5. Slack delivers the same trusted KPI to the team", 10_000),
    ("slack-retention-drivers.png", "6. The assistant explains retention drivers", 10_000),
    ("slack-priority-segment.png", "7. The assistant recommends a priority sales segment", 10_000),
]


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    filenames = ["DejaVuSans-Bold.ttf", "arialbd.ttf"] if bold else ["DejaVuSans.ttf", "arial.ttf"]
    for filename in filenames:
        try:
            return ImageFont.truetype(filename, size)
        except OSError:
            continue
    return ImageFont.load_default()


def title_frame() -> Image.Image:
    frame = Image.new("RGB", CANVAS_SIZE, "#111827")
    draw = ImageDraw.Draw(frame)
    title_font = load_font(42, bold=True)
    body_font = load_font(24)
    draw.text((60, 205), "Telecom Customer Usage Pipeline", fill="#F9FAFB", font=title_font)
    draw.text(
        (60, 285),
        "Airflow -> Spark -> Databricks -> Godrisoft Insights -> Slack",
        fill="#38BDF8",
        font=body_font,
    )
    draw.text((60, 345), "From raw customer data to business action", fill="#D1D5DB", font=body_font)
    return frame


def screenshot_frame(filename: str, caption: str) -> Image.Image:
    source = Image.open(SCREENSHOTS / filename).convert("RGB")
    content = ImageOps.contain(source, IMAGE_AREA, Image.Resampling.LANCZOS)
    frame = Image.new("RGB", CANVAS_SIZE, "#0B1220")
    x = (IMAGE_AREA[0] - content.width) // 2
    y = (IMAGE_AREA[1] - content.height) // 2
    frame.paste(content, (x, y))

    draw = ImageDraw.Draw(frame)
    draw.rectangle((0, 540, 960, 620), fill="#111827")
    draw.text((30, 563), caption, fill="#F9FAFB", font=load_font(23, bold=True))
    return frame


def main() -> None:
    missing = [filename for filename, _, _ in SCENES if not (SCREENSHOTS / filename).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing demo screenshots: {', '.join(missing)}")

    frames = [title_frame()]
    durations = [8_000]
    for filename, caption, duration in SCENES:
        frames.append(screenshot_frame(filename, caption))
        durations.append(duration)

    palette_frames = [frame.quantize(colors=128, method=Image.Quantize.MEDIANCUT) for frame in frames]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    palette_frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=palette_frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"Created {OUTPUT.relative_to(PROJECT_ROOT)} ({sum(durations) / 1000:.0f} seconds)")


if __name__ == "__main__":
    main()
