# Backward-compat re-export: moved to hledger-core
from hledger_core.date_extractor import *  # noqa: F401,F403
from hledger_core.date_extractor import (  # explicit for type checkers
    can_swap_day_and_month,
    extract_dates_times,
    get_date_from_bank_date_or_shop_date_description,
    get_day_from_date,
    get_hour_from_date,
    get_minute_from_date,
    get_month_from_date,
    get_year_from_date,
    is_within_date_range,
    parse_date,
    swap_month_day,
)
