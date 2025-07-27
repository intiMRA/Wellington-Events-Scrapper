from datetime import datetime
import pytz  # pip install pytz

def is_facebook_url_expired_now(oe_hex):
    # Get current time in NZ
    nz_timezone = pytz.timezone('Pacific/Auckland')
    now_nz = datetime.now(nz_timezone)

    # Decode Facebook's OE timestamp (UTC)
    unix_time = int(oe_hex, 16)
    utc_expiry = datetime.utcfromtimestamp(unix_time).replace(tzinfo=pytz.utc)

    # Convert expiry to NZ time
    nz_expiry = utc_expiry.astimezone(nz_timezone)

    # Compare
    return now_nz > nz_expiry