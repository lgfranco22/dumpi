#!/usr/bin/env python3
# dumpi.py
"""
Coleta informações técnicas do sistema, grava em arquivo texto e faz upload para servidor.
"""

import os
import re
import platform
import socket
import json
import warnings
from datetime import datetime

warnings.filterwarnings("ignore", category=DeprecationWarning)

# obter nome (tenta USERDOMAIN, depois COMPUTERNAME, depois hostname)
computer = os.environ.get('USERDOMAIN') or os.environ.get('COMPUTERNAME') or __import__('socket').gethostname()

# sanitizar para evitar caracteres inválidos em nomes de arquivo
computer = re.sub(r'[\\/:\*\?"<>\|]', '_', computer)

# gerar timestamp no formato desejado: DD-MM-YYYY_HH-MM
ts = datetime.now().strftime('%d-%m-%Y_%H-%M')

# nome final
filename = f"{computer}_{ts}.txt"
# exemplo: DESKTOP-UP2V8_30-09-2025_22-53.txt

try:
    import psutil
except ImportError:
    raise SystemExit("Instale 'psutil' antes: pip install psutil")

try:
    import requests
except ImportError:
    raise SystemExit("Instale 'requests' antes: pip install requests")

# obter nome (tenta USERDOMAIN, depois COMPUTERNAME, depois hostname)
computer = os.environ.get('USERDOMAIN') or os.environ.get('COMPUTERNAME') or __import__('socket').gethostname()

# sanitizar para evitar caracteres inválidos em nomes de arquivo
computer = re.sub(r'[\\/:\*\?"<>\|]', '_', computer)

# gerar timestamp no formato desejado: DD-MM-YYYY_HH-MM
ts = datetime.now().strftime('%d-%m-%Y_%H-%M')

OUTPUT_FILE = f"{computer}_{ts}.txt"

UPLOAD_URL = "https://www.site.com/upload.php"  # <--- ajuste para o seu servidor
AUTH_TOKEN = None  # se desejar usar token, defina aqui (opcional)


def gather_system_info():
    info = {}
    info["timestamp"] = datetime.utcnow().isoformat() + "Z"
    info["platform"] = {
        "system": platform.system(),
        "node": platform.node(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }

    # CPU
    try:
        cpu_freq = psutil.cpu_freq()
        info["cpu"] = {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_processors": psutil.cpu_count(logical=True),
            "usage_percent_per_core": psutil.cpu_percent(interval=1, percpu=True),
            "avg_usage_percent": psutil.cpu_percent(interval=0.5),
            "freq_mhz": cpu_freq._asdict() if cpu_freq is not None else None,
        }
    except Exception as e:
        info["cpu"] = {"error": str(e)}

    # Memory
    try:
        vm = psutil.virtual_memory()
        info["memory"] = {
            "total_bytes": vm.total,
            "available_bytes": vm.available,
            "used_bytes": vm.used,
            "percent": vm.percent,
        }
    except Exception as e:
        info["memory"] = {"error": str(e)}

    # Swap
    try:
        sw = psutil.swap_memory()
        info["swap"] = sw._asdict()
    except Exception as e:
        info["swap"] = {"error": str(e)}

    # Disks
    try:
        disks = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except PermissionError:
                usage = None
            disks.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "opts": part.opts,
                "usage": usage._asdict() if usage is not None else None
            })
        info["disks"] = disks
    except Exception as e:
        info["disks"] = {"error": str(e)}

    # Partições / I/O
    try:
        disk_io = psutil.disk_io_counters()
        info["disk_io"] = disk_io._asdict() if disk_io is not None else None
    except Exception as e:
        info["disk_io"] = {"error": str(e)}

    # Rede
    try:
        net_if_addrs = {}
        for ifname, addrs in psutil.net_if_addrs().items():
            addrs_list = []
            for a in addrs:
                addrs_list.append({
                    "family": str(a.family),
                    "address": a.address,
                    "netmask": a.netmask,
                    "broadcast": a.broadcast,
                    "ptp": a.ptp
                })
            net_if_addrs[ifname] = addrs_list
        info["network_interfaces"] = net_if_addrs
        info["net_io"] = psutil.net_io_counters()._asdict()
    except Exception as e:
        info["network"] = {"error": str(e)}

    # Processos (ex.: top 5 por CPU)
    try:
        procs = []
        for p in sorted(psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]), key=lambda x: x.info.get("cpu_percent", 0), reverse=True)[:5]:
            pi = p.info
            mem = None
            if pi.get("memory_info"):
                mem = {"rss": pi["memory_info"].rss, "vms": pi["memory_info"].vms}
            procs.append({"pid": pi.get("pid"), "name": pi.get("name"), "cpu_percent": pi.get("cpu_percent"), "memory": mem})
        info["top_processes"] = procs
    except Exception as e:
        info["top_processes"] = {"error": str(e)}

    # Hostname/IP
    try:
        info["hostname"] = socket.gethostname()
        info["local_ip"] = socket.gethostbyname(info["hostname"])
    except Exception:
        info["local_ip"] = None

    return info


def save_to_text(info, filename=OUTPUT_FILE):
    # Salvamos JSON formatado e também uma versão "human readable"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("=== System Info (JSON) ===\n")
        f.write(json.dumps(info, indent=2, ensure_ascii=False))
        f.write("\n\n=== System Info (Readable) ===\n")
        f.write(f"Sistema: {info['platform']['system']} {info['platform']['release']}\n")
        f.write(f"Máquina: {info['platform']['machine']}\n")
        f.write(f"Processador (string): {info['platform']['processor']}\n")
        f.write(f"Hostname: {info.get('hostname')}\n")
        f.write(f"IP local: {info.get('local_ip')}\n")
        f.write(f"Memória total (bytes): {info['memory'].get('total_bytes')}\n")
        f.write(f"Memória uso (%): {info['memory'].get('percent')}\n")
        f.write("Discos:\n")
        for d in info.get("disks", []):
            f.write(f"  - {d.get('device')} montado em {d.get('mountpoint')} tipo {d.get('fstype')}\n")
    return filename


def upload_file(filepath, url=UPLOAD_URL, token=AUTH_TOKEN):
    if not os.path.isfile(filepath):
        raise FileNotFoundError("Arquivo para upload não encontrado: " + filepath)

    files = {"file": (os.path.basename(filepath), open(filepath, "rb"))}
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.post(url, files=files, headers=headers, timeout=30, verify=True)
    return resp


def main():
    info = gather_system_info()
    fname = save_to_text(info)
    print(f"Arquivo gerado: {fname}")
    try:
        resp = upload_file(fname)
        print("Upload status:", resp.status_code)
        print("Resposta do servidor:", resp.text)
        os.system("pause")
    except Exception as e:
        print("Falha no upload:", e)
        os.system("pause")


if __name__ == "__main__":
    main()
