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
from .receive import (
    DmrdReceiveActivity,
    DmrdReceiveEvent,
    parse_dmrd_receive_event,
)
from .parrot_profile import (
    LOCKED_PARROT_PROFILE,
    PARROT_DESTINATION_ID,
    PARROT_ECHO_CAP_SECONDS,
    PARROT_TIMESLOT,
    PARROT_TRANSMIT_CAP_SECONDS,
    LockedParrotTestProfile,
    ParrotSafetyError,
    ParrotTestPlan,
    build_locked_parrot_fixture,
    build_locked_parrot_test_plan,
)
from .parrot_live import (
    ParrotLiveError,
    ParrotLiveResult,
    execute_locked_parrot_once,
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
    "DmrdReceiveActivity",
    "DmrdReceiveEvent",
    "LoginState",
    "LOCKED_PARROT_PROFILE",
    "LockedParrotTestProfile",
    "PARROT_DESTINATION_ID",
    "PARROT_ECHO_CAP_SECONDS",
    "PARROT_TIMESLOT",
    "PARROT_TRANSMIT_CAP_SECONDS",
    "ParrotSafetyError",
    "ParrotLiveError",
    "ParrotLiveResult",
    "ParrotTestPlan",
    "SILENT_CALL_PACKET_COUNT",
    "SILENT_VOICE_BURST_COUNT",
    "SilentCallFixture",
    "build_auth_packet",
    "build_close_packet",
    "build_config_packet",
    "build_login_packet",
    "build_ping_packet",
    "build_locked_parrot_fixture",
    "build_locked_parrot_test_plan",
    "execute_locked_parrot_once",
    "build_tg91_terminator_with_lc",
    "build_tg91_ts2_silent_call_fixture",
    "build_tg91_voice_frame",
    "build_tg91_voice_lc_header",
    "build_tg91_voice_sync",
    "is_master_ack",
    "is_master_nak",
    "is_master_pong",
    "parse_dmrd_packet",
    "parse_dmrd_receive_event",
]

from .parrot_voice import ParrotVoiceError, ParrotVoiceResult, build_locked_parrot_voice_packets, execute_locked_parrot_voice_once
