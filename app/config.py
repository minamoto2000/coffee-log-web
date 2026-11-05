from zoneinfo import ZoneInfo

# Calendar dates (e.g. days since roast) are evaluated in the user's local
# timezone, because a roast date printed on a bag is a local date.
APP_TIMEZONE = ZoneInfo("Asia/Tokyo")
