from pathlib import Path
import wave
from carendmr.diagnostics.audio_lab import analyze_pcm16, build_session_report

def _wav(path,samples,rate=8000):
 import array
 path.parent.mkdir(parents=True,exist_ok=True); pcm=array.array("h",samples)
 with wave.open(str(path),"wb") as f: f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate); f.writeframes(pcm.tobytes())

def test_audio_metrics_detect_clipping():
 m=analyze_pcm16([32767,-32768,1000,-1000],8000); assert m.clipping_samples>=2; assert m.peak_dbfs>-0.1

def test_audio_lab_builds_json_and_html(tmp_path):
 _wav(tmp_path/"01_test.wav",[0,1000,-1000]*100); report=build_session_report(tmp_path); assert report.exists(); assert (tmp_path/"analysis.json").exists()

def test_measurement_points_exist():
 tx=Path("carendmr/application/audio_send_service.py").read_text(encoding="utf-8"); rx=Path("carendmr/brandmeister/listen.py").read_text(encoding="utf-8")
 for name in ("01_mikrofon_roh_16k.wav","02_nach_mic_gain_16k.wav","03_vor_ambe_8k.wav","04_ambe_frames.bin"): assert name in tx
 for name in ("05_nach_ambe_decoder_8k.wav","06_vor_lautsprecher_8k.wav"): assert name in rx
