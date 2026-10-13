from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from app.assets import assets
from app.forms import fmt_num
from app.services.clock import to_local

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

_ICONS = {
    "today": '<path d="M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z"/>',
    "history": '<path d="M4 20V11M10 20V5M16 20v-6M22 20H2"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "foods": '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3l-5.6 2.9 1.1-6.2L3 9.6l6.2-.9z"/>',
    "settings": '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/>'
    '<circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
}


def icon(name: str) -> Markup:
    return Markup(
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{_ICONS[name]}</svg>'
    )


def fmt_day(value: date, today: date | None = None) -> str:
    if today is not None:
        if value == today:
            return "Today"
        if value == today - timedelta(days=1):
            return "Yesterday"
    return value.strftime("%a, %b %d").replace(" 0", " ")


def fmt_time(value: datetime, tz: str) -> str:
    return to_local(value, tz).strftime("%I:%M %p").lstrip("0")


templates.env.filters["num"] = fmt_num
templates.env.filters["day"] = fmt_day
templates.env.filters["time"] = fmt_time
templates.env.globals["icon"] = icon
templates.env.globals["static_url"] = assets.url
templates.env.globals["asset_version"] = assets.version
