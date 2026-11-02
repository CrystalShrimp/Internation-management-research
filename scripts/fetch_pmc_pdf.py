"""Download a PMC supplementary PDF by solving the cloudpmc-viewer proof-of-work challenge."""
import re
import sys
import hashlib
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def solve_pow(challenge: str, difficulty: int) -> int:
    prefix = "0" * difficulty
    nonce = 0
    while True:
        if hashlib.sha256((challenge + str(nonce)).encode()).hexdigest().startswith(prefix):
            return nonce
        nonce += 1


def fetch(url: str, out_path: str) -> None:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "text/html,application/pdf,*/*"})
    s.headers["Referer"] = "https://pmc.ncbi.nlm.nih.gov/"
    r = s.get(url, timeout=60)
    if r.headers.get("content-type", "").startswith("application/pdf"):
        with open(out_path, "wb") as f:
            f.write(r.content)
        print("direct download ok")
        return
    m = re.search(r'POW_CHALLENGE\s*=\s*"([^"]+)"', r.text)
    d = re.search(r"POW_DIFFICULTY\s*=\s*\"(\d+)\"", r.text)
    name = re.search(r'POW_COOKIE_NAME\s*=\s*"([^"]+)"', r.text)
    if not m:
        raise RuntimeError(f"no challenge found; got {r.status_code} {r.text[:200]}")
    challenge, diff = m.group(1), int(d.group(1)) if d else 4
    cookie_name = name.group(1) if name else "cloudpmc-viewer-pow"
    nonce = solve_pow(challenge, diff)
    print(f"challenge={challenge[:20]}... difficulty={diff} nonce={nonce}")
    s.cookies.set(cookie_name, f"{challenge},{nonce}", domain="pmc.ncbi.nlm.nih.gov", path="/")
    r2 = s.get(url, timeout=120)
    if r2.headers.get("content-type", "").startswith("application/pdf"):
        with open(out_path, "wb") as f:
            f.write(r2.content)
        print(f"saved {out_path} ({len(r2.content)} bytes)")
    else:
        raise RuntimeError(f"still not pdf: {r2.status_code} {r2.text[:300]}")


if __name__ == "__main__":
    fetch(sys.argv[1], sys.argv[2])
