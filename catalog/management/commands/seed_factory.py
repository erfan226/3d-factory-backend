"""Seed processes, materials, categories, tags, showcase items and products.

Placeholder images are generated with Pillow and every seeded object is
flagged as placeholder via its admin_note field.
"""
import random
from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile

from catalog.models import Category, Material, Process, Product, ProductImage, ProductOption, ShowcaseImage, ShowcaseItem, ShowcaseFile, Tag
from content.models import SiteSetting

PALETTE = [
    (("#EDF1F3", "#B3BEC6"), "grey"),
    (("#D8BFAE", "#9B7665"), "tan"),
    (("#E8F0F4", "#6093AA"), "sky"),
    (("#FFFFFF", "#D3D4DA"), "white"),
]

SHOWCASE_SEEDS = [
    ("vase-prints", "مجموعه گلدان‌های چاپی", "household", "fdm", "pla"),
    ("cable-clips", "نگهدارنده کابل مدولار", "household", "fdm", "petg"),
    ("drill-guide", "راهنمای مته دقیق", "tools", "fdm", "petg"),
    ("parametric-bracket", "براکت قابل تنظیم", "spare-parts", "fdm", "pla"),
    ("resin-miniatures", "مینیاتورهای رزینی", "games", "sla", "resin"),
    ("jewelry-molds", "قالب جواهرسازی", "art", "sla", "resin"),
    ("aluminium-gopro-mount", "هولدر آلومینیومی دوربین", "gadgets", "cnc", "aluminium-6061"),
    ("steel-machine-parts", "قطعات ماشین‌کاری فولادی", "spare-parts", "cnc", "steel"),
    ("laser-lamp-shade", "آباژور برش لیزری", "art", "laser", "plywood"),
    ("acrylic-signage", "تابلو اکریلیک", "fashion", "laser", "acrylic"),
    ("classroom-skeleton", "اسکلت آموزشی کلاس", "education", "fdm", "pla"),
    ("gear-keychain", "جاسوئیچی چرخ‌دنده‌ای", "gadgets", "fdm", "pla"),
]

PRODUCT_SEEDS = [
    ("custom-fdm-print", "چاپ FDM سفارشی", "fdm", "pla", 250_000, 3),
    ("custom-sla-print", "چاپ SLA رزینی", "sla", "resin", 480_000, 4),
    ("cnc-aluminium-part", "ماشین‌کاری آلومینیوم", "cnc", "aluminium-6061", 1_900_000, 7),
    ("cnc-steel-part", "ماشین‌کاری فولاد", "cnc", "steel", 2_400_000, 8),
    ("laser-plywood-cut", "برش لیزری تخته سه‌لایی", "laser", "plywood", 320_000, 2),
    ("laser-acrylic-cut", "برش لیزری اکریلیک", "laser", "acrylic", 380_000, 2),
    ("petg-functional-parts", "قطعات فانکشنال PETG", "fdm", "petg", 310_000, 3),
    ("finishing-service", "پرداخت سطح و رنگ", "fdm", "pla", 180_000, 2),
]


def _hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _placeholder_image(width, height, palette, seed_text=""):
    from PIL import Image, ImageDraw

    top, bottom = (_hex_to_rgb(c) for c in palette[0])
    img = Image.new("RGB", (width, height), top)
    draw = ImageDraw.Draw(img)
    # Soft vertical gradient
    for y in range(height):
        blend = y / max(height - 1, 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * blend) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)
    # Geometric accents (no text; fonts are frontend-only)
    rng = random.Random(seed_text or f"{width}x{height}")
    for _ in range(6):
        x0 = rng.randint(0, width - 80)
        y0 = rng.randint(0, height - 80)
        size = rng.randint(24, 90)
        draw.ellipse([x0, y0, x0 + size, y0 + size], outline=(255, 255, 255), width=2)
    import io

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88)
    return out.getvalue()


class Command(BaseCommand):
    help = "Seed factory catalog data (idempotent)."

    def handle(self, *args, **options):
        self.stdout.write("Seeding processes...")
        processes = {
            "fdm": Process.objects.update_or_create(
                slug="fdm",
                defaults={
                    "name": "FDM",
                    "description": "چاپ سه‌بعدی filament با پلاستیک‌های مهندسی",
                    "quote_type": "estimate",
                    "sort_order": 1,
                },
            )[0],
            "sla": Process.objects.update_or_create(
                slug="sla",
                defaults={
                    "name": "SLA",
                    "description": "چاپ رزینی با جزئیات بالا",
                    "quote_type": "manual",
                    "sort_order": 2,
                },
            )[0],
            "cnc": Process.objects.update_or_create(
                slug="cnc",
                defaults={
                    "name": "CNC",
                    "description": "ماشین‌کاری فلز و پلیمر",
                    "quote_type": "manual",
                    "needs_drawing": True,
                    "sort_order": 3,
                },
            )[0],
            "laser": Process.objects.update_or_create(
                slug="laser",
                defaults={
                    "name": "Laser",
                    "description": "برش و حکاکی لیزری",
                    "quote_type": "manual",
                    "sort_order": 4,
                },
            )[0],
            "other": Process.objects.update_or_create(
                slug="other",
                defaults={"name": "Other", "description": "سایر خدمات", "quote_type": "manual", "sort_order": 5},
            )[0],
        }

        self.stdout.write("Seeding materials...")
        materials = {}
        material_defs = [
            ("pla", "PLA", "fdm", ["white", "black", "silver", "tan"]),
            ("petg", "PETG", "fdm", ["white", "black", "translucent"]),
            ("resin", "Resin", "sla", ["grey", "black", "clear"]),
            ("aluminium-6061", "Aluminium 6061", "cnc", ["natural"]),
            ("steel", "Steel", "cnc", ["natural", "black oxide"]),
            ("plywood", "Plywood", "laser", ["natural"]),
            ("acrylic", "Acrylic", "laser", ["clear", "black", "frosted"]),
        ]
        for slug, name, process_slug, colors in material_defs:
            materials[slug] = Material.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "process": processes[process_slug],
                    "colors": colors,
                    "price_tier": "medium",
                },
            )[0]

        self.stdout.write("Seeding categories and tags...")
        category_slugs = [
            "household", "tools", "gadgets", "art", "education", "spare-parts", "fashion", "games",
        ]
        categories = {}
        for index, slug in enumerate(category_slugs):
            categories[slug] = Category.objects.update_or_create(
                slug=slug,
                defaults={"name": slug.replace("-", " ").title(), "sort_order": index},
            )[0]
        tags = {}
        for tag_name in ["functional", "household", "spare part", "gift", "educational", "prototype"]:
            tags[tag_name] = Tag.objects.update_or_create(
                slug=tag_name.replace(" ", "-"),
                defaults={"name": tag_name},
            )[0]

        self.stdout.write("Seeding showcase items...")
        for index, (slug, title, category_slug, process_slug, material_slug) in enumerate(SHOWCASE_SEEDS):
            item, created = ShowcaseItem.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "summary": f"{title} — نمونه‌کار تولیدشده در کارگاه با کیفیت بالا و تنظیمات چاپ بهینه.",
                    "description": (
                        f"{title}\n\n"
                        "این مدل در کارگاه تولید و تست شده است.\n\n"
                        "تنظیمات چاپ:\n"
                        "- ارتفاع لایه: ۰.۲ میلی‌متر\n"
                        "- Infill: ۲۰٪\n"
                        "- Support: در صورت نیاز\n\n"
                        "توجه: تصاویر این نمونه placeholder هستند و پیش از انتشار نهایی با عکس واقعی جایگزین می‌شوند."
                    ),
                    "category": categories[category_slug],
                    "process": processes[process_slug],
                    "material": materials[material_slug],
                    "license": "cc-by" if index % 3 == 0 else ("cc-by-nc" if index % 3 == 1 else "factory-only"),
                    "allow_download": index % 2 == 0,
                    "is_featured": index < 3,
                    "is_active": True,
                    "admin_note": "placeholder images — seeded by seed_factory",
                },
            )
            if created or not item.images.exists():
                image_data = _placeholder_image(1200, 900, PALETTE[index % len(PALETTE)], slug)
                item.cover_image.save(f"{slug}-cover.jpg", ContentFile(image_data), save=False)
                item.save()
                ShowcaseImage.objects.create(
                    item=item,
                    image=ContentFile(image_data, name=f"{slug}-1.jpg"),
                    sort_order=0,
                )
                ShowcaseImage.objects.create(
                    item=item,
                    image=ContentFile(
                        _placeholder_image(1200, 900, PALETTE[(index + 1) % len(PALETTE)], f"{slug}-b"),
                        name=f"{slug}-2.jpg",
                    ),
                    sort_order=1,
                )
            if created or not item.files.exists():
                stl_stub = (
                    b"solid placeholder\nendsolid placeholder\n"
                )
                ShowcaseFile.objects.create(
                    item=item,
                    file=ContentFile(stl_stub, name=f"{slug}.stl"),
                    original_name=f"{slug}.stl",
                    file_type="stl",
                    size_bytes=len(stl_stub),
                    is_preview_model=True,
                )
            item.tags.add(tags["functional"], tags["prototype"] if index % 2 else tags["gift"])

        self.stdout.write("Seeding products...")
        for index, (slug, title, process_slug, material_slug, price_from, lead_days) in enumerate(PRODUCT_SEEDS):
            if not price_from:
                self.stdout.write(self.style.ERROR(f"Product {slug} has no price_from — aborting."))
                raise SystemExit(1)
            product, created = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "description": (
                        f"{title} با کیفیت تضمین‌شده کارگاه. قیمت شروع از {price_from:,} تومان. "
                        "توجه: تصاویر محصول placeholder هستند."
                    ),
                    "process": processes[process_slug],
                    "material": materials[material_slug],
                    "price_from": price_from,
                    "lead_time_days": lead_days,
                    "is_orderable": True,
                    "is_active": True,
                    "admin_note": "placeholder images — seeded by seed_factory",
                },
            )
            if created or not product.images.exists():
                product.cover_image.save(
                    f"{slug}-cover.jpg",
                    ContentFile(_placeholder_image(1200, 900, PALETTE[(index + 2) % len(PALETTE)], slug)),
                    save=False,
                )
                product.save()
                ProductImage.objects.create(
                    product=product,
                    image=ContentFile(
                        _placeholder_image(1200, 900, PALETTE[(index + 3) % len(PALETTE)], f"{slug}-b"),
                        name=f"{slug}-1.jpg",
                    ),
                    sort_order=0,
                )
            ProductOption.objects.update_or_create(
                product=product,
                defaults={
                    "name": "اندازه",
                    "values": ["کوچک", "متوسط", "بزرگ"],
                    "price_delta": [0, 120_000, 280_000],
                },
            )

        site = SiteSetting.load()
        self.stdout.write(self.style.SUCCESS("Factory seed complete."))
