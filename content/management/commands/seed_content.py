"""Seed SiteSetting and five Persian blog posts (idempotent)."""
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from content.models import BlogPost, SiteSetting


POSTS = [
    {
        "slug": "fdm-vs-sla",
        "title": "FDM یا SLA؛ کدام روش برای پروژه شما مناسب است؟",
        "summary": "مقایسه دو روش رایج چاپ سه‌بعدی از نظر دقت، هزینه و سرعت.",
        "body": (
            "انتخاب بین FDM و SLA به نوع پروژه بستگی دارد.\n\n"
            "FDM برای قطعات فانکشنال، پروتوتایپ‌های بزرگ و هزینه کمتر مناسب است. "
            "دقت لایه‌ها در FDM حدود ۰.۲ میلی‌متر است و برای بیشتر کاربردهای صنعتی کافی است.\n\n"
            "SLA برای جزئیات بالا، مینیاتور و قطعات نرم و صاف بهتر عمل می‌کند. "
            "پس از چاپ، قطعات رزینی نیاز به شست‌وشو و cure دارند.\n\n"
            "در کارگاه ما هر دو روش ارائه می‌شود؛ اگر مطمئن نیستید، فایل را ارسال کنید تا پیشنهاد فنی بدهیم."
        ),
        "category": "آموزش",
    },
    {
        "slug": "choosing-material-fdm",
        "title": "راهنمای انتخاب متریال: PLA یا PETG؟",
        "summary": "تفاوت‌های کلیدی PLA و PETG برای قطعات کاربردی.",
        "body": (
            "PLA ارزان‌تر، تمیزتر و برای نمایشی عالی است؛ اما در برابر حرارت ضعیف‌تر است.\n\n"
            "PETG مقاوم‌تر، انعطاف‌پذیرتر و برای قطعات مکانیکی و نگهدارنده‌ها انتخاب بهتری است.\n\n"
            "برای قطعات بیرونی و در معرض آفتاب، PETG با UV-stabilizer پیشنهاد می‌شود."
        ),
        "category": "متریال",
    },
    {
        "slug": "cnc-design-tips",
        "title": "نکات طراحی فایل برای ماشین‌کاری CNC",
        "summary": "چطور فایل STEP خود را برای CNC آماده کنیم.",
        "body": (
            "برای ماشین‌کاری، فایل STEP یا IGES با واحد میلی‌متر ارسال کنید.\n\n"
            "شمش‌ها حداقل ۳ میلی‌متر و گوشه‌های داخلی شعاع فرز را در نظر بگیرید. "
            "دیواره‌های نازک‌تر از ۱ میلی‌متر معمولاً غیرقابل اجرا هستند.\n\n"
            "اگر نقشه فنی دارید، همراه فایل ارسال کنید؛ برای CNC نقشه لازم است."
        ),
        "category": "CNC",
    },
    {
        "slug": "post-processing-guide",
        "title": "پرداخت سطح: از سنباده تا رنگ",
        "summary": "مراحل پرداخت قطعات چاپی برای نتیجه حرفه‌ای.",
        "body": (
            "پرداخت سطح شامل سنباده، پرایمر، رنگ و پولیش است.\n\n"
            "برای قطعات نمایشی، پرایمر سنباده ۴۰۰ و سپس رنگ اسپری نتیجه خوبی می‌دهد. "
            "برای قطعات رزینی، سمباده خیس ۸۰۰ تا ۲۰۰۰ سطح آینه‌ای می‌سازد.\n\n"
            "خدمات finishing کارگاه شامل هر سه مرحله است."
        ),
        "category": "پرداخت",
    },
    {
        "slug": "lead-time-explained",
        "title": "زمان تحویل سفارش‌ها چگونه محاسبه می‌شود؟",
        "summary": "عوامل موثر بر lead time و نحوه پیگیری سفارش.",
        "body": (
            "زمان تحویل به فرآیند، متریال و صف تولید بستگی دارد.\n\n"
            "میانگین چاپ FDM سه روز کاری، SLA چهار روز و ماشین‌کاری CNC هفت روز است. "
            "پس از تایید پیش‌فاکتور، سفارش وارد صف تولید می‌شود و از داشبورد قابل پیگیری است."
        ),
        "category": "فرآیند",
    },
]


class Command(BaseCommand):
    help = "Seed content app data (idempotent)."

    def handle(self, *args, **options):
        self.stdout.write("Seeding site settings...")
        site = SiteSetting.load()
        changed = False
        if site.site_name in ("کارگاه سه‌بعدی", ""):
            site.site_name = "کارگاه سه‌بعدی"
            changed = True
        if not site.working_hours:
            site.working_hours = "شنبه تا چهارشنبه، ۹ تا ۱۸"
            changed = True
        if not site.expected_reply_text:
            site.expected_reply_text = "کارشناسان ما حداکثر ظرف یک روز کاری پاسخ می‌دهند."
            changed = True
        if changed:
            site.save()

        self.stdout.write("Seeding blog posts...")
        for index, post in enumerate(POSTS):
            blog, created = BlogPost.objects.update_or_create(
                slug=post["slug"],
                defaults={
                    "title": post["title"],
                    "summary": post["summary"],
                    "body": post["body"],
                    "category": post["category"],
                    "is_published": True,
                    "published_at": timezone.now() - timezone.timedelta(days=index * 3),
                    "admin_note": "placeholder cover — seeded by seed_content",
                },
            )
            if not blog.cover:
                import io

                from PIL import Image, ImageDraw

                img = Image.new("RGB", (1200, 700), (216, 191, 174))
                draw = ImageDraw.Draw(img)
                draw.ellipse([80, 80, 300, 300], outline=(255, 255, 255), width=3)
                draw.ellipse([900, 400, 1120, 620], outline=(255, 255, 255), width=3)
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                blog.cover.save(f"{blog.slug}-cover.jpg", ContentFile(buffer.getvalue()), save=True)

        self.stdout.write(self.style.SUCCESS("Content seed complete."))
