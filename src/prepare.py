#!/usr/bin/env python3
"""ViceDrops6 Free: gera uma fila para agendamento humano via ChatGPT/Metricool.

Nao chama a API do Metricool e nao publica automaticamente.
"""
from __future__ import annotations
import argparse
import csv
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "inbox" / "clips.csv"
CONFIG = ROOT / "config" / "settings.json"
USAGE = ROOT / "state" / "usage.json"
PROCESSED = ROOT / "state" / "scheduled_clip_ids.txt"
OUT = ROOT / "output"
FIELDS = ["clip_id", "network", "scheduled_at", "filename", "media_url", "caption", "credit", "status"]
NETWORKS = ("tiktok", "instagram")
MONTHLY_MAX = 20


def yes(s):
    return str(s).strip().casefold() in {"sim", "s", "yes", "true", "1"}


def monthkey(d: date) -> str:
    return d.strftime("%Y-%m")


def safe_filename(s: str) -> bool:
    return bool(s) and not s.startswith(("/", "\\")) and ".." not in s and "\n" not in s and "\r" not in s


def validate_row(row):
    clip = row.get("clip_id", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,80}", clip):
        return "clip_id precisa ter 3-80 caracteres (letras, números, _ ou -)"
    if not safe_filename(row.get("filename", "").strip()):
        return "filename é obrigatório (sem caminhos ou ..)"
    if not row.get("caption", "").strip():
        return "caption é obrigatória"
    if not yes(row.get("approved", "")) or not yes(row.get("rights_cleared", "")):
        return "aprovação editorial e autorização de direitos devem ser 'sim'"
    if not row.get("credit", "").strip():
        return "credit obrigatório para identificar origem do conteúdo"
    media_url = row.get("media_url", "").strip()
    if media_url and not media_url.startswith("https://"):
        return "media_url deve ser HTTPS ou vazio"
    networks = row.get("platforms", "both").strip().lower()
    if networks not in {"both", "tiktok", "instagram"}:
        return "platforms deve ser both, tiktok ou instagram"
    return None


def load_clips(path=INPUT, processed_path=PROCESSED):
    if not path.exists():
        raise ValueError(f"Arquivo ausente: {path}")
    processed = set()
    if processed_path.exists():
        processed = {x.strip() for x in processed_path.read_text(encoding="utf-8").splitlines() if x.strip() and not x.startswith("#")}
    good, rejected, seen = [], [], set()
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or not {"clip_id", "filename", "caption", "approved", "rights_cleared", "credit"}.issubset(reader.fieldnames):
            raise ValueError("Cabeçalho CSV inválido; confira inbox/exemplo.csv")
        for line, row in enumerate(reader, start=2):
            if all(not (v or "").strip() for v in row.values() if isinstance(v, str)):
                continue
            err = validate_row(row)
            clip_id = (row.get("clip_id") or "").strip()
            if clip_id in seen:
                err = "clip_id duplicado no CSV"
            seen.add(clip_id)
            if clip_id in processed:
                continue
            if err:
                rejected.append(f"Linha {line} ({clip_id or 'sem id'}): {err}")
                continue
            good.append({k: (v or "").strip() for k, v in row.items() if k is not None})
    return good, rejected


def month_usage(month: str, usage: dict):
    entry = usage.get(month)
    if not isinstance(entry, dict) or not isinstance(entry.get("published"), int) or not isinstance(entry.get("already_scheduled"), int):
        return None
    if entry["published"] < 0 or entry["already_scheduled"] < 0:
        return None
    return entry["published"] + entry["already_scheduled"]


def plan(clips, settings, usage, today: date):
    tz = ZoneInfo(settings.get("timezone", "America/Sao_Paulo"))
    interval = int(settings.get("days_between_clips", 3))
    if interval < 1 or interval > 31:
        raise ValueError("days_between_clips deve ser de 1 a 31")
    start_delay = int(settings.get("start_delay_days", 1))
    if start_delay < 0 or start_delay > 31:
        raise ValueError("start_delay_days deve ser entre 0 e 31")
    times = settings.get("slots", {})
    for network in NETWORKS:
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", times.get(network, "")):
            raise ValueError(f"Horário inválido para {network}")
    # Sem números manuais do Metricool, não criamos nenhuma fila: evita exceder o plano Free.
    approved = []
    alerts = []
    reserved = {}
    cursor = today + timedelta(days=start_delay)
    for clip in clips:
        networks = NETWORKS if clip.get("platforms", "both").lower() == "both" else (clip["platforms"].lower(),)
        needed = len(networks)
        chosen = None
        for _ in range(366):
            ym = monthkey(cursor)
            already = month_usage(ym, usage)
            if already is None:
                alerts.append(f"Informe published e already_scheduled em state/usage.json para {ym}. Nenhuma publicação futura desse mês será preparada.")
                break
            left = MONTHLY_MAX - already - reserved.get(ym, 0)
            if left >= needed:
                chosen = cursor
                break
            cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
        if chosen is None:
            break
        ym = monthkey(chosen)
        reserved[ym] = reserved.get(ym, 0) + needed
        for network in networks:
            hh, mm = map(int, times[network].split(":"))
            when = datetime(chosen.year, chosen.month, chosen.day, hh, mm, tzinfo=tz).isoformat(timespec="minutes")
            credit = clip["credit"]
            caption = clip["caption"]
            if credit.lower() not in caption.lower():
                caption += f" | Créditos: {credit}"
            approved.append({"clip_id": clip["clip_id"], "network": network,
                "scheduled_at": when, "filename": clip["filename"],
                "media_url": clip.get("media_url", ""), "caption": caption,
                "credit": credit, "status": "PRECISA_AGENDAR"})
        cursor = chosen + timedelta(days=interval)
    return approved, list(dict.fromkeys(alerts))


def main(today_override=None):
    OUT.mkdir(exist_ok=True)
    settings = json.loads(CONFIG.read_text(encoding="utf-8"))
    usage = json.loads(USAGE.read_text(encoding="utf-8"))
    today = today_override or datetime.now(ZoneInfo(settings["timezone"])).date()
    clips, rejected = load_clips()
    planned, alerts = plan(clips, settings, usage, today)
    target = OUT / "fila_para_agendar.csv"
    with target.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader(); w.writerows(planned)
    report = ["# ViceDrops6 — fila para agendamento", "",
        f"Data de preparação: {today.isoformat()}",
        f"Clipes autorizados elegíveis: {len(clips)}",
        f"Publicações planejadas: {len(planned)}", "",
        "**IMPORTANTE:** Este processo NÃO enviou nada ao Metricool ou ao TikTok/Instagram.",
        "Envie os MP4 correspondentes e o arquivo fila_para_agendar.csv ao ChatGPT para agendar manualmente.", "",
        "## Avisos"]
    report.extend(f"- {a}" for a in alerts)
    if not alerts:
        report.append("- Nenhum")
    report.extend(["", "## Linhas rejeitadas"])
    report.extend(f"- {r}" for r in rejected)
    if not rejected:
        report.append("- Nenhuma")
    report.extend(["", "## Agendamentos sugeridos", "", "| Rede | Data/hora | Arquivo |", "|---|---|---|"])
    report.extend(f"| {p['network']} | {p['scheduled_at']} | {p['filename']} |" for p in planned)
    report.extend(["", "Depois de agendar, anote os IDs dos clipes em state/scheduled_clip_ids.txt e atualize state/usage.json com os totais reais do Metricool."])
    (OUT / "resumo.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Clipes elegíveis: {len(clips)} | agendamentos sugeridos: {len(planned)} | recusados: {len(rejected)}")
    for a in alerts: print("AVISO:", a)
    print("Gerados output/fila_para_agendar.csv e output/resumo.md; nenhum post enviado.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", help="Para testes: YYYY-MM-DD")
    args = ap.parse_args()
    main(date.fromisoformat(args.today) if args.today else None)
