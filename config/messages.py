"""Central Persian error messages and machine-readable error codes."""

# Machine-readable codes
FILE_TOO_LARGE = "file_too_large"
INVALID_FILE_TYPE = "invalid_file_type"
TOO_MANY_FILES = "too_many_files"
QUOTE_EXPIRED = "quote_expired"
QUOTE_ALREADY_USED = "quote_already_used"
QUOTE_NOT_SENT = "quote_not_sent"
PAYMENT_FAILED = "payment_failed"
PAYMENT_NOT_ALLOWED = "payment_not_allowed"
NOT_FOUND = "not_found"
VALIDATION_ERROR = "validation_error"
AUTHENTICATION_FAILED = "authentication_failed"
PERMISSION_DENIED = "permission_denied"
DOWNLOAD_NOT_ALLOWED = "download_not_allowed"
NO_MODEL_FILE = "no_model_file"
NO_IMAGE = "no_image"
MISSING_FIELD = "missing_field"

# English -> Persian translations for common DRF messages
error_messages = {
    "This field is required.": "این فیلد الزامی است.",
    "This field may not be blank.": "این فیلد نمی‌تواند خالی باشد.",
    "This field may not be null.": "این فیلد نمی‌تواند خالی باشد.",
    "A valid integer is required.": "یک عدد صحیح معتبر وارد کنید.",
    "A valid URL is required.": "آدرس اینترنتی معتبر وارد کنید.",
    "Enter a valid email address.": "آدرس ایمیل معتبر وارد کنید.",
    "A user with that email already exists.": "کاربری با این ایمیل قبلاً ثبت‌نام کرده است.",
    "No active account found with the given credentials": "ایمیل یا رمز عبور اشتباه است.",
    "Authentication credentials were not provided.": "برای این عملیات باید وارد حساب خود شوید.",
    "Given token not valid for any token type": "نشست شما منقضی شده است. دوباره وارد شوید.",
    "Invalid page.": "شماره صفحه معتبر نیست.",
    "Not found.": "موردی یافت نشد.",
    "Permission denied.": "اجازه انجام این عملیات را ندارید.",
    "This field is not allowed.": "این فیلد مجاز نیست.",
    "You do not have permission to perform this action.": "اجازه انجام این عملیات را ندارید.",
}

PERSIAN_ERRORS = {
    FILE_TOO_LARGE: "حجم فایل بیشتر از حد مجاز (۱۰۰ مگابایت) است.",
    INVALID_FILE_TYPE: "نوع فایل مجاز نیست. فرمت‌های مجاز را بررسی کنید.",
    TOO_MANY_FILES: "حداکثر ۵ فایل برای هر درخواست مجاز است.",
    QUOTE_EXPIRED: "اعتبار این پیش‌فاکتور به پایان رسیده است.",
    QUOTE_ALREADY_USED: "این پیش‌فاکتور قبلاً تایید شده است.",
    QUOTE_NOT_SENT: "پیش‌فاکتور قابل تایید نیست.",
    PAYMENT_FAILED: "پرداخت انجام نشد. لطفاً دوباره تلاش کنید.",
    PAYMENT_NOT_ALLOWED: "این سفارش قابل پرداخت نیست.",
    DOWNLOAD_NOT_ALLOWED: "دانلود این فایل مجاز نیست.",
    NO_MODEL_FILE: "برای انتشار حداقل یک فایل مدل لازم است.",
    NO_IMAGE: "برای انتشار حداقل یک تصویر لازم است.",
    VALIDATION_ERROR: "اطلاعات ارسالی معتبر نیست.",
    NOT_FOUND: "موردی یافت نشد.",
}
