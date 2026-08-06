"""Messbare Audio-Diagnose für den CarenDMR-Sprachpfad."""
from __future__ import annotations
import json, math, wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

@dataclass(frozen=True, slots=True)
class AudioMetrics:
    sample_rate: int; samples: int; duration_seconds: float
    peak_dbfs: float; rms_dbfs: float; crest_factor_db: float
    clipping_samples: int; clipping_percent: float
    dc_offset: float; zero_crossing_rate: float
    dominant_frequency_hz: float; spectral_centroid_hz: float
    low_band_percent: float; speech_band_percent: float; high_band_percent: float

def _db(value: float) -> float:
    return -120.0 if value <= 1e-12 else 20.0 * math.log10(value)

def analyze_pcm16(samples: Iterable[int], sample_rate: int) -> AudioMetrics:
    import numpy as np
    pcm=np.asarray(tuple(samples),dtype=np.float64)
    if pcm.size==0:
        return AudioMetrics(sample_rate,0,0.0,-120.0,-120.0,0.0,0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0)
    x=pcm/32768.0; abs_x=np.abs(x); peak=float(np.max(abs_x)); rms=float(np.sqrt(np.mean(x*x)))
    clipping=int(np.count_nonzero(abs_x >= (32760.0/32768.0)))
    zcr=float(np.mean(np.diff(np.signbit(x)))) if x.size>1 else 0.0
    window=np.hanning(x.size); spectrum=np.abs(np.fft.rfft(x*window))**2; freqs=np.fft.rfftfreq(x.size,1.0/sample_rate)
    total=float(np.sum(spectrum)); dominant=float(freqs[int(np.argmax(spectrum))]) if spectrum.size else 0.0
    centroid=float(np.sum(freqs*spectrum)/total) if total>0 else 0.0
    def band(lo,hi):
        if total<=0:return 0.0
        mask=(freqs>=lo)&(freqs<hi); return float(np.sum(spectrum[mask])/total*100.0)
    return AudioMetrics(sample_rate,int(x.size),float(x.size/sample_rate),_db(peak),_db(rms),max(0.0,_db(peak)-_db(rms)),clipping,float(clipping/x.size*100.0),float(np.mean(x)),zcr,dominant,centroid,band(0,120),band(120,min(3400,sample_rate/2)),band(min(3400,sample_rate/2),sample_rate/2+1))

def read_wav(path: Path):
    import array, sys
    with wave.open(str(path),'rb') as f:
        if f.getnchannels()!=1 or f.getsampwidth()!=2: raise ValueError(f'Nur Mono-PCM16 wird analysiert: {path}')
        rate=f.getframerate(); raw=f.readframes(f.getnframes())
    pcm=array.array('h'); pcm.frombytes(raw)
    if sys.byteorder!='little': pcm.byteswap()
    return rate,tuple(int(v) for v in pcm)

def _plot_wav(path: Path, output_dir: Path):
    try:
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception:return []
    rate,samples=read_wav(path); x=np.asarray(samples,dtype=np.float64)/32768.0
    if x.size<8:return []
    t=np.arange(x.size)/rate; created=[]
    fig,ax=plt.subplots(figsize=(10,3.2)); ax.plot(t,x,linewidth=.6); ax.grid(True,alpha=.25); ax.set_title(path.name+' – Wellenform'); ax.set_xlabel('Zeit [s]'); ax.set_ylabel('Amplitude'); target=output_dir/(path.stem+'_waveform.png'); fig.tight_layout(); fig.savefig(target,dpi=130); plt.close(fig); created.append(target.name)
    fig,ax=plt.subplots(figsize=(10,3.2)); spec=20*np.log10(np.maximum(np.abs(np.fft.rfft(x*np.hanning(x.size))),1e-9)); ax.plot(np.fft.rfftfreq(x.size,1/rate),spec,linewidth=.7); ax.grid(True,alpha=.25); ax.set_title(path.name+' – Spektrum'); ax.set_xlabel('Frequenz [Hz]'); ax.set_ylabel('Pegel [dB]'); target=output_dir/(path.stem+'_spectrum.png'); fig.tight_layout(); fig.savefig(target,dpi=130); plt.close(fig); created.append(target.name)
    nfft=min(512,max(64,x.size//8)); noverlap=min(48,nfft-1); step=max(1,nfft-noverlap)
    frames=[]
    for start in range(0,max(1,x.size-nfft+1),step):
        frame=x[start:start+nfft]
        if frame.size<nfft: frame=np.pad(frame,(0,nfft-frame.size))
        frames.append(np.abs(np.fft.rfft(frame*np.hanning(nfft)))**2)
    power=np.asarray(frames,dtype=np.float64).T
    power_db=10.0*np.log10(np.maximum(power,1e-12))
    freq_axis=np.fft.rfftfreq(nfft,1.0/rate)
    time_axis=np.arange(power_db.shape[1],dtype=np.float64)*step/rate
    fig,ax=plt.subplots(figsize=(10,4.2)); ax.pcolormesh(time_axis,freq_axis,power_db,shading='auto'); ax.set_title(path.name+' – Spektrogramm'); ax.set_xlabel('Zeit [s]'); ax.set_ylabel('Frequenz [Hz]'); target=output_dir/(path.stem+'_spectrogram.png'); fig.tight_layout(); fig.savefig(target,dpi=130); plt.close(fig); created.append(target.name)
    return created

def build_session_report(session_dir: Path, *, extra: dict|None=None) -> Path:
    session_dir=Path(session_dir); reports={}; images={}
    for wav_path in sorted(session_dir.glob('*.wav')):
        rate,samples=read_wav(wav_path); reports[wav_path.name]=asdict(analyze_pcm16(samples,rate)); images[wav_path.name]=_plot_wav(wav_path,session_dir)
    payload={'files':reports,'extra':extra or {}}; (session_dir/'analysis.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    rows=[]
    for name,m in reports.items():
        warning='CLIPPING' if m['clipping_percent']>0 else ''
        rows.append(f"<tr><td>{name}</td><td>{m['duration_seconds']:.3f}</td><td>{m['peak_dbfs']:.2f}</td><td>{m['rms_dbfs']:.2f}</td><td>{m['crest_factor_db']:.2f}</td><td>{m['clipping_percent']:.4f}</td><td>{m['spectral_centroid_hz']:.0f}</td><td>{warning}</td></tr>")
    galleries=''.join(f'<h2>{name}</h2>'+''.join(f'<img src="{img}" style="max-width:100%;display:block;margin:8px 0">' for img in imgs) for name,imgs in images.items())
    html=f"<!doctype html><html lang='de'><meta charset='utf-8'><title>CarenDMR Audioanalyse</title><style>body{{font-family:sans-serif;max-width:1200px;margin:2rem auto;background:#111;color:#eee}}table{{border-collapse:collapse;width:100%}}th,td{{padding:.5rem;border:1px solid #555;text-align:right}}th:first-child,td:first-child{{text-align:left}}</style><h1>CarenDMR Audioanalyse</h1><table><tr><th>Datei</th><th>Dauer s</th><th>Peak dBFS</th><th>RMS dBFS</th><th>Crest dB</th><th>Clipping %</th><th>Spektralzentrum Hz</th><th>Warnung</th></tr>{''.join(rows)}</table>{galleries}</html>"
    target=session_dir/'analysis.html'; target.write_text(html,encoding='utf-8'); return target
