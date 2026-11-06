"""Log every state change of the therm-gateway to CSV (for calibration runs).

usage: python log_states.py <gateway host> <secrets.yaml> <out.csv>
Runs until killed; reconnects if the API drops.
"""
import asyncio, csv, re, sys, time
from aioesphomeapi import APIClient


async def run(host, key, out):
    w = csv.writer(out)
    while True:
        cli = APIClient(host, 6053, None, noise_psk=key)
        try:
            await cli.connect(login=True)
            entities, _ = await cli.list_entities_services()
            names = {e.key: e.name for e in entities}

            def on_state(s):
                if s.key in names:
                    w.writerow([f"{time.time():.3f}", names[s.key], s.state])
                    out.flush()

            cli.subscribe_states(on_state)
            while True:
                await asyncio.sleep(5)
                if not cli._connection or not cli._connection.is_connected:
                    raise ConnectionError("api dropped")
        except Exception as e:
            w.writerow([f"{time.time():.3f}", "#error", repr(e)])
            out.flush()
            try:
                await cli.disconnect()
            except Exception:
                pass
            await asyncio.sleep(3)


host, secrets, out_csv = sys.argv[1:4]
key = re.search(r'api_encryption_key: "(.*)"', open(secrets).read()).group(1)
with open(out_csv, "a", newline="") as f:
    asyncio.run(run(host, key, f))
