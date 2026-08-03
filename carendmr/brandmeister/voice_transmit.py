"""Allgemeiner DMR-Sprachsender für dynamische Ziele."""
from __future__ import annotations
import secrets, time
from dataclasses import dataclass
from carendmr.encoder import AmbeEncoder
from .client import BrandMeisterClient
from .config import BrandMeisterConfig
from .dmrd import DmrdCallType, DmrdDataType, DmrdFrameClass, DmrdPacket
from .parrot_profile import PARROT_TRANSMIT_CAP_SECONDS, ParrotSafetyError
from .protocol import LoginState
from carendmr.diagnostics.tx_rx_timing import mark as timing_mark
from .silent_call import _MS_AUDIO_SYNC, _add_sync, _bits_to_bytes, _encode_embedded_lc, _encode_full_lc_burst, _EMB_CODEWORDS

PACKET_INTERVAL_SECONDS=0.060
PCM_FRAME_SAMPLES=160
AMBE_FRAME_BYTES=9

@dataclass(frozen=True, slots=True)
class VoiceTransmitResult:
    authenticated: bool
    sent_packets: int
    voice_bursts_sent: int
    transmit_elapsed_seconds: float
    closed: bool
    echo_received: bool=False
    echo_voice_bursts: int=0
    timed_out: bool=False
    decoded_codewords: int=0
    output_samples: int=0
    decode_errors: int=0

def _pack_ambe(codewords):
    packed=b''.join(codewords); burst=bytearray(33)
    burst[:13]=packed[:13]; burst[13]=packed[13]&0xF0; burst[19]=packed[13]&0x0F; burst[20:33]=packed[14:27]
    return burst

def _apply_embedded_lc(burst, number, embedded):
    lcss=0
    if 1 <= number < 5:
        fragment=embedded[(number-1)*32:number*32]
        packed=_bits_to_bytes((False,)*4+fragment+(False,)*4)
        burst[14]=(burst[14]&0xF0)|(packed[0]&0x0F); burst[15:18]=packed[1:4]; burst[18]=(burst[18]&0x0F)|(packed[4]&0xF0)
        lcss=1 if number==1 else 2 if number==4 else 3
    else:
        burst[14]&=0xF0; burst[15:18]=b'\x00\x00\x00'; burst[18]&=0x0F
    codeword=_EMB_CODEWORDS[lcss]; emb0,emb1=codeword>>8,codeword&0xFF
    burst[13]=(burst[13]&0xF0)|((emb0>>4)&0x0F); burst[14]=(burst[14]&0x0F)|((emb0<<4)&0xF0)
    burst[18]=(burst[18]&0xF0)|((emb1>>4)&0x0F); burst[19]=(burst[19]&0x0F)|((emb1<<4)&0xF0)

def build_voice_packets(*, source_id, repeater_id, destination_id, timeslot, call_type, stream_id, first_sequence, pcm_samples, encoder):
    if not pcm_samples: raise ValueError('Die TX-Aufnahme ist leer.')
    if not 1 <= destination_id <= 0xFFFFFF: raise ValueError('Die Ziel-ID ist ungültig.')
    if timeslot not in (1,2): raise ValueError('Timeslot muss 1 oder 2 sein.')
    frames=[]
    for offset in range(0,len(pcm_samples),PCM_FRAME_SAMPLES):
        frame=pcm_samples[offset:offset+PCM_FRAME_SAMPLES]
        if len(frame)<PCM_FRAME_SAMPLES: frame=frame+(0,)*(PCM_FRAME_SAMPLES-len(frame))
        encoded=encoder.encode_2450x1150(frame)
        if len(encoded)!=AMBE_FRAME_BYTES: raise ParrotSafetyError('Der Encoder lieferte keinen 9-Byte-AMBE-Rahmen.')
        frames.append(encoded)
    while len(frames)%3: frames.append(encoder.encode_2450x1150((0,)*PCM_FRAME_SAMPLES))
    flco=0x03 if call_type is DmrdCallType.PRIVATE else 0x00
    lc=bytes((flco,0,0))+destination_id.to_bytes(3,'big')+source_id.to_bytes(3,'big')
    embedded=_encode_embedded_lc(lc); packets=[]; sequence=first_sequence
    def add(payload, frame_class, *, voice_no=None, data_type=None):
        nonlocal sequence
        packets.append(DmrdPacket(sequence,source_id,destination_id,repeater_id,timeslot,call_type,frame_class,stream_id,payload,voice_frame_number=voice_no,data_type=data_type))
        sequence=(sequence+1)&0xFF
    add(_encode_full_lc_burst(lc,0x01),DmrdFrameClass.DATA_SYNC,data_type=DmrdDataType.VOICE_LC_HEADER.value)
    for burst_index in range(0,len(frames),3):
        number=(burst_index//3)%6; burst=_pack_ambe(tuple(frames[burst_index:burst_index+3]))
        if number==0: _add_sync(burst,_MS_AUDIO_SYNC); add(bytes(burst),DmrdFrameClass.VOICE_SYNC)
        else: _apply_embedded_lc(burst,number,embedded); add(bytes(burst),DmrdFrameClass.VOICE,voice_no=number)
    add(_encode_full_lc_burst(lc,0x02),DmrdFrameClass.DATA_SYNC,data_type=DmrdDataType.TERMINATOR_WITH_LC.value)
    return tuple(packets)

def execute_voice_once(config: BrandMeisterConfig, *, destination_id:int, timeslot:int, call_type:DmrdCallType, pcm_samples:tuple[int,...], encoder:AmbeEncoder, client_factory=BrandMeisterClient, sequence_factory=lambda:secrets.randbelow(256), stream_factory=lambda:secrets.randbelow(0xFFFFFFFF)+1, monotonic=time.monotonic, sleep=time.sleep):
    packets=build_voice_packets(source_id=config.dmr_id,repeater_id=config.dmr_id,destination_id=destination_id,timeslot=timeslot,call_type=call_type,stream_id=stream_factory(),first_sequence=sequence_factory(),pcm_samples=pcm_samples,encoder=encoder)
    client=client_factory(config); sent=voice=0; authenticated=False; closed=False; start=0.0
    try:
        timing_mark("TX_LOGIN_START")
        client.login(); timing_mark("TX_LOGIN_FERTIG"); authenticated=client.state is LoginState.CONNECTED
        if not authenticated or client.transport is None: raise RuntimeError('BrandMeister-Anmeldung fehlgeschlagen.')
        start=monotonic()
        timing_mark("TX_ERSTER_FRAME_START")
        for index,packet in enumerate(packets):
            if monotonic()-start >= PARROT_TRANSMIT_CAP_SECONDS: raise RuntimeError('Die Sendezeitgrenze wurde erreicht.')
            raw=packet.to_bytes()
            if client.transport.send(raw)!=len(raw): raise RuntimeError('Ein DMRD-Paket wurde nicht vollständig gesendet.')
            sent+=1
            if sent == 1: timing_mark("TX_ERSTER_FRAME_GESENDET")
            if packet.frame_class in (DmrdFrameClass.VOICE,DmrdFrameClass.VOICE_SYNC): voice+=1
            if index+1<len(packets): sleep(PACKET_INTERVAL_SECONDS)
        elapsed=monotonic()-start
        timing_mark("TX_LETZTER_FRAME_GESENDET")
    finally:
        client.close(); timing_mark("TX_VERBINDUNG_GESCHLOSSEN"); closed=client.transport is None and client.state is LoginState.DISCONNECTED
    return VoiceTransmitResult(authenticated,sent,voice,elapsed,closed)
