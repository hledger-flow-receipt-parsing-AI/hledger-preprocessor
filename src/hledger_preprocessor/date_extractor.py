# Backward-compat re-export: moved to hledger-core
from hledger_core.date_extractor import *  # noqa: F401,F403
from hledger_core.date_extractor import (  # explicit for type checkers
    get_date_from_bank_date_or_shop_date_description,
    is_within_date_range,
    parse_date,
    get_month_from_date,
    get_year_from_date,
    get_day_from_date,
    get_hour_from_date,
    get_minute_from_date,
    extract_dates_times,
    can_swap_day_and_month,
    swap_month_day,
)
