"""BrandMeister-/MMDVM-Protokollgrundlage."""

from .client import (
    BrandMeisterClient,
    BrandMeisterLoginError,
    BrandMeisterLoginResult,
)
from .config import BrandMeisterConfig, BrandMeisterConfigStore
from .dmrd import (
    DMRD_PACKET_SIZE,
    DMRD_PAYLOAD_SIZE,
    TARGET_TALKGROUP,
    TARGET_TIMESLOT,
    DmrdCallType,
    DmrdDataType,
    DmrdFrameClass,
    DmrdPacket,
    build_tg91_terminator_with_lc,
    build_tg91_voice_frame,
    build_tg91_voice_lc_header,
    build_tg91_voice_sync,
    parse_dmrd_packet,
)
from .protocol import (
    LoginState,
    build_auth_packet,
    build_close_packet,
    build_config_packet,
    build_login_packet,
    build_ping_packet,
    is_master_ack,
    is_master_nak,
    is_master_pong,
)
from .silent_call import (
    SILENT_CALL_PACKET_COUNT,
    SILENT_VOICE_BURST_COUNT,
    SilentCallFixture,
    build_tg91_ts2_silent_call_fixture,
)

__all__ = [
    "BrandMeisterClient",
    "BrandMeisterConfig",
    "BrandMeisterConfigStore",
    "BrandMeisterLoginError",
    "BrandMeisterLoginResult",
    "DMRD_PACKET_SIZE",
    "DMRD_PAYLOAD_SIZE",
    "TARGET_TALKGROUP",
    "TARGET_TIMESLOT",
    "DmrdCallType",
    "DmrdDataType",
    "DmrdFrameClass",
    "DmrdPacket",
    "LoginState",
    "SILENT_CALL_PACKET_COUNT",
    "SILENT_VOICE_BURST_COUNT",
    "SilentCallFixture",
    "build_auth_packet",
    "build_close_packet",
    "build_config_packet",
    "build_login_packet",
    "build_ping_packet",
    "build_tg91_terminator_with_lc",
    "build_tg91_ts2_silent_call_fixture",
    "build_tg91_voice_frame",
    "build_tg91_voice_lc_header",
    "build_tg91_voice_sync",
    "is_master_ack",
    "is_master_nak",
    "is_master_pong",
    "parse_dmrd_packet",
]
