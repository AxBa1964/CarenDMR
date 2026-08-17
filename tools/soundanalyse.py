import sys
import os
import numpy as np
import librosa

def analyze_wav(file_path):
    if not os.path.exists(file_path):
        print(f"Fehler: Datei '{file_path}' wurde nicht gefunden.")
        return

    print(f"\nLade und analysiere: {file_path} ...")
    y, sr = librosa.load(file_path, sr=None)
    duration = len(y) / sr
    
    # Peak & Clipping Check
    max_peak = np.max(np.abs(y))
    clipped_samples = np.sum(np.abs(y) >= 0.999)
    peak_db = 20 * np.log10(max_peak) if max_peak > 0 else -100
    
    # RMS / Durchschnittslautstärke
    rms_val = np.sqrt(np.mean(y**2))
    rms_db = 20 * np.log10(rms_val) if rms_val > 0 else -100
    
    # Frequenz-Analyse
    S = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    mean_spectrum = np.mean(S, axis=1)
    
    total_energy = np.sum(mean_spectrum)
    cum_energy = np.cumsum(mean_spectrum)
    cutoff_idx = np.searchsorted(cum_energy, 0.995 * total_energy)
    estimated_cutoff = freqs[cutoff_idx]

    # Auslese-Ergebnisse
    print("=" * 45)
    print(f" Dauer:                {duration:.2f} Sekunden")
    print(f" Sample-Rate:          {sr} Hz")
    print(f" Spitzenpegel (Peak):  {peak_db:.2f} dBFS")
    print(f" Clipping-Stellen:     {clipped_samples} Samples")
    print(f" Durchschnitt (RMS):   {rms_db:.2f} dBFS")
    print(f" Frequenz-Limit:       ~{estimated_cutoff:.0f} Hz")
    print("=" * 45)
    
    # Bewertung
    if sr >= 44100 and estimated_cutoff > 20000:
        print("-> Ergebnis: Echtes Unkomprimiertes Lossless-Audio")
    elif estimated_cutoff < 16500:
        print("-> Achtung: Frequenzgang entspricht stark komprimiertem Audio (<= 128 kbps)!")
    else:
        print("-> Hinweis: Leicht beschränkte Bandbreite / mp3-Konvertierung möglich")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_wav(sys.argv[1])
    else:
        print("Bitte gib eine WAV-Datei an. Beispiel:")
        print("python soundanalyse.py test.wav")