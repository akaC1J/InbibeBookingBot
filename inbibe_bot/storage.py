from typing import Dict, List, Set

from inbibe_bot.models import Booking, UserState

# In-memory storage for user states and bookings
user_states: Dict[int, UserState] = {}
bookings: Dict[str, Booking] = {}

# Tracks alternative date/time requests: booking_id -> admin message_id
alt_requests: Dict[str, int] = {}

# Tracks table selection prompt messages in admin group: booking_id -> message_id
table_requests: Dict[str, int] = {}

# Queue of approved (ready) bookings to be delivered via API
ready_bookings: List[Booking] = []

# Track which ready bookings have been delivered by /api/bookings
ready_delivered_ids: Set[str] = set()


