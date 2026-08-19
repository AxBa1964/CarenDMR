from __future__ import annotations
import argparse, json, sys, time, re
from datetime import datetime
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from carendmr.application.encoder_service import EncoderService
from carendmr.brandmeister.config import BrandMeisterConfigStore
from carendmr.brandmeister.dmrd import DmrdCallType
from carendmr.brandmeister.live_voice_transmit import execute_live_voice_once
from carendmr.diagnostics.tx_rx_timing import (
    initialize as timing_initialize,
    start_cycle as timing_start_cycle,
    attach_session as timing_attach_session,
    detach_session as timing_detach_session,
    mark as timing_mark,
)

RATE=8000; CHUNK=160

def load_pcm(path: Path):
    data, sr = sf.read(path, dtype='float32', always_2d=True)
    mono = data.mean(axis=1)
    if sr != RATE:
        from math import gcd
        g=gcd(int(sr), RATE); mono=resample_poly(mono, RATE//g, int(sr)//g)
    pcm=np.clip(np.rint(mono*32767.0), -32768, 32767).astype(np.int16)
    return pcm

def chunks(pcm):
    for i in range(0,len(pcm),CHUNK): yield tuple(int(x) for x in pcm[i:i+CHUNK])


def timing_metrics(timeline_path: Path):
    try:
        payload=json.loads(timeline_path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    events=payload.get('events', [])
    metrics={}
    for ev in events:
        step=ev.get('step')
        detail=str(ev.get('detail',''))
        if step == 'TX_JITTER_STATISTIK':
            for key in ('AbstandAvgMs','MinMs','MaxMs','JitterRmsMs','TaktResets','ZuSpaet','ZuFrueh'):
                m=re.search(rf'(?:^|;){key}=([-+0-9.]+)', detail)
                if m:
                    val=float(m.group(1))
                    metrics[key]=int(val) if key in {'TaktResets','ZuSpaet','ZuFrueh'} else round(val,3)
        elif step == 'TX_ENCODER_STATISTIK':
            m=re.search(r'MaxMs=([-+0-9.]+)', detail)
            if m: metrics['EncoderMaxMs']=round(float(m.group(1)),3)
        elif step == 'PARROT_ECHO_WARTE_ENDE':
            metrics['ParrotEnde']=detail
    return metrics

def main():
    ap=argparse.ArgumentParser(description='CarenDMR TG9990 Parrot regression')
    ap.add_argument('--sound-dir', default=str(ROOT/'Sound'))
    ap.add_argument('--pause', type=float, default=3.0)
    ap.add_argument('--count', type=int, default=10)
    args=ap.parse_args()
    sound=Path(args.sound_dir)
    files=[sound/f'{i}_AB.mp3' for i in range(1,args.count+1)]
    missing=[str(p) for p in files if not p.is_file()]
    if missing: raise SystemExit('Fehlende Referenzdateien: '+', '.join(missing))
    cfg=BrandMeisterConfigStore(ROOT/'config'/'brandmeister.local.json').load()
    enc_service=EncoderService(ROOT)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    outdir=ROOT/'logs'/'parrot_regression'/stamp; outdir.mkdir(parents=True, exist_ok=True)
    rows=[]
    global_timing_log = timing_initialize(ROOT)
    print(f'CarenDMR Parrot-Regression: {len(files)} Fälle, TG9990 TS2 Privat')
    print(f'Timing-Log: {global_timing_log}')
    for n,path in enumerate(files,1):
        pcm=load_pcm(path); duration=len(pcm)/RATE
        print(f'[{n}/{len(files)}] {path.name}: {duration:.2f}s – sende ...', flush=True)
        testdir = outdir / f'{n:02d}_{path.stem}'
        testdir.mkdir(parents=True, exist_ok=True)
        timing_start_cycle(f'REGRESSION {n:02d}/{len(files)} {path.name} TG=9990 TS=2 PRIVATE')
        timeline_path = timing_attach_session(testdir)
        timing_mark('REGRESSION_TEST_START', f'Datei={path.name};Dauer={duration:.3f}s')
        encoder=enc_service.create_transmit_encoder(); started=time.monotonic()
        try:
            result=execute_live_voice_once(cfg,destination_id=9990,timeslot=2,call_type=DmrdCallType.PRIVATE,
                pcm_chunks=chunks(pcm),encoder=encoder,wait_for_parrot_echo=True,lead_in_seconds=0.240)
            ok=bool(result.echo_received) and not bool(result.timed_out)
            row={'test':n,'file':path.name,'duration_s':round(duration,3),'pass':ok,
                 'echo_received':bool(result.echo_received),'echo_voice_bursts':int(result.echo_voice_bursts),
                 'timed_out':bool(result.timed_out),'tx_elapsed_s':round(float(result.transmit_elapsed_seconds),3),
                 'decode_errors':int(result.decode_errors),'wall_s':round(time.monotonic()-started,3),
                 'timeline':str(timeline_path.relative_to(ROOT))}
            timing_mark('REGRESSION_TEST_RESULT',
                        f"Ergebnis={'PASS' if ok else 'FAIL'};EchoBursts={row['echo_voice_bursts']};"
                        f"DecodeFehler={row['decode_errors']};Timeout={int(row['timed_out'])}")
            print(f"    {'PASS' if ok else 'FAIL'} – EchoBursts={row['echo_voice_bursts']} DecodeFehler={row['decode_errors']}")
        except Exception as exc:
            row={'test':n,'file':path.name,'duration_s':round(duration,3),'pass':False,
                 'error':f'{type(exc).__name__}: {exc}','wall_s':round(time.monotonic()-started,3),
                 'timeline':str(timeline_path.relative_to(ROOT))}
            timing_mark('REGRESSION_TEST_FEHLER', row['error'])
            print(f"    FAIL – {row['error']}")
        finally:
            close=getattr(encoder,'close',None)
            if callable(close): close()
            timing_mark('REGRESSION_TEST_ENDE', f'Datei={path.name}')
            timing_detach_session()
        row.update(timing_metrics(timeline_path))
        rows.append(row)
        (outdir/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if n < len(files):
            print(f'    Pause {args.pause:.1f}s ...', flush=True); time.sleep(args.pause)
    passed=sum(1 for r in rows if r.get('pass')); pct=100.0*passed/len(rows)
    summary=f'CarenDMR Parrot-Regression {stamp}\nPASS: {passed}/{len(rows)} = {pct:.1f}%\n'
    for r in rows:
        timing = ''
        if 'MaxMs' in r:
            timing = f" | TX Max={r['MaxMs']:.1f} ms | Jitter={r.get('JitterRmsMs',0):.1f} ms | Resets={r.get('TaktResets',0)}"
        summary += f"{r['test']:02d} {r['file']}: {'PASS' if r.get('pass') else 'FAIL'}{timing}" + (f" – {r.get('error')}" if r.get('error') else '') + '\n'
    (outdir/'summary.txt').write_text(summary,encoding='utf-8'); print('\n'+summary); print('Ergebnis:',outdir)
    return 0 if passed==len(rows) else 2
if __name__=='__main__': raise SystemExit(main())
