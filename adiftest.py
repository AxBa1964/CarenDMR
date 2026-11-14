import socket
import datetime

# ---------------------------------------------------------
# Funktion: ADIF-QSO erzeugen
# ---------------------------------------------------------
def build_adif(call, band, mode, tg=None, ts=None):
    now = datetime.datetime.now()
    qso_date = now.strftime("%Y%m%d")
    time_on = now.strftime("%H%M%S")

    adif = (
        f"<CALL:{len(call)}>{call} "
        f"<QSO_DATE:8>{qso_date} "
        f"<TIME_ON:6>{time_on} "
        f"<BAND:{len(band)}>{band} "
        f"<MODE:{len(mode)}>{mode} "
    )

    # Optional: DMR-spezifische Felder
    if tg is not None:
        adif += f"<DMR_TG:{len(str(tg))}>{tg} "
    if ts is not None:
        adif += f"<DMR_TS:1>{ts} "

    adif += "<EOR>"
    return adif


# ---------------------------------------------------------
# Funktion: ADIF-QSO via UDP an HRD senden
# ---------------------------------------------------------
def send_to_hrd(adif_string, host="127.0.0.1", port=2237):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(adif_string.encode("utf-8"), (host, port))
    sock.close()


# ---------------------------------------------------------
# Beispiel: DMR-QSO simulieren und senden
# ---------------------------------------------------------
def simulate_dmr_qso():
    # Beispielwerte eines empfangenen DMR-QSO
    call = "DO1DPL"
    band = "70CM"
    mode = "DMR"
    tg = 262
    ts = 1

    # ADIF bauen
    adif = build_adif(call, band, mode, tg, ts)

    # Senden
    send_to_hrd(adif)

    print("Gesendet an HRD:")
    print(adif)


# ---------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------
if __name__ == "__main__":
    simulate_dmr_qso()
