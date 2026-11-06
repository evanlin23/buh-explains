"""Microsoft device-code login -> Minecraft access token, for the owner's own account.

  python3 auth.py login    # prints a code to enter at microsoft.com/link, waits, saves work/auth.json
  python3 auth.py token    # refreshes and prints nothing; writes work/session.json (name, uuid, token)

The refresh token is the long-lived secret. Locally it lives in work/auth.json (mode 600,
gitignored). On CI it comes from the MC_REFRESH_TOKEN secret and the rotated value is written back
to work/auth.json. Never print or commit either token.
"""
import json
import os
import pathlib
import sys
import time
import urllib.parse
import urllib.request

# Public client id of Microsoft's own Minecraft/Xbox app; supports the device-code flow on live.com.
CLIENT_ID = "00000000402b5328"
SCOPE = "service::user.auth.xboxlive.com::MBI_SSL"
WORK = pathlib.Path(__file__).resolve().parent / "work"
AUTH, SESSION = WORK / "auth.json", WORK / "session.json"


def post(url, data, form=True, headers=None):
    body = urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode()
    h = {"Content-Type": "application/x-www-form-urlencoded" if form else "application/json", "Accept": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, body, h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:
            raise RuntimeError(f"{url}: HTTP {e.code}") from None


def save(path, obj):
    WORK.mkdir(exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f)


def minecraft_from_ms(ms_access):
    xbl = post("https://user.auth.xboxlive.com/user/authenticate", {
        "Properties": {"AuthMethod": "RPS", "SiteName": "user.auth.xboxlive.com", "RpsTicket": ms_access},
        "RelyingParty": "http://auth.xboxlive.com", "TokenType": "JWT"}, form=False)
    uhs = xbl["DisplayClaims"]["xui"][0]["uhs"]
    xsts = post("https://xsts.auth.xboxlive.com/xsts/authorize", {
        "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbl["Token"]]},
        "RelyingParty": "rp://api.minecraftservices.com/", "TokenType": "JWT"}, form=False)
    if "Token" not in xsts:
        raise RuntimeError(f"XSTS refused (XErr {xsts.get('XErr')})")
    mc = post("https://api.minecraftservices.com/authentication/login_with_xbox",
              {"identityToken": f"XBL3.0 x={uhs};{xsts['Token']}"}, form=False)
    if "access_token" not in mc:
        raise RuntimeError(f"Minecraft login refused: {mc.get('errorMessage') or mc.get('error')}")
    req = urllib.request.Request("https://api.minecraftservices.com/minecraft/profile",
                                 headers={"Authorization": f"Bearer {mc['access_token']}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            prof = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"No Minecraft Java profile on this account (HTTP {e.code})") from None
    save(SESSION, {"name": prof["name"], "uuid": prof["id"], "token": mc["access_token"], "expires": time.time() + mc.get("expires_in", 86400)})
    return prof["name"]


def login():
    dc = post("https://login.live.com/oauth20_connect.srf", {"client_id": CLIENT_ID, "scope": SCOPE, "response_type": "device_code"})
    print(f"Go to {dc['verification_uri']} and enter code {dc['user_code']} (expires in {dc['expires_in'] // 60} min)", flush=True)
    deadline = time.time() + dc["expires_in"]
    while time.time() < deadline:
        time.sleep(dc.get("interval", 5))
        tok = post("https://login.live.com/oauth20_token.srf", {
            "client_id": CLIENT_ID, "grant_type": "urn:ietf:params:oauth:grant-type:device_code", "device_code": dc["device_code"]})
        if "access_token" in tok:
            save(AUTH, {"refresh_token": tok["refresh_token"]})
            print("logged in as", minecraft_from_ms(tok["access_token"]), flush=True)
            return 0
        if tok.get("error") not in ("authorization_pending", "slow_down"):
            print("login failed:", tok.get("error"), flush=True)
            return 1
    print("code expired", flush=True)
    return 1


def token():
    rt = os.environ.get("MC_REFRESH_TOKEN") or json.loads(AUTH.read_text())["refresh_token"]
    tok = post("https://login.live.com/oauth20_token.srf", {
        "client_id": CLIENT_ID, "scope": SCOPE, "grant_type": "refresh_token", "refresh_token": rt})
    if "access_token" not in tok:
        print("refresh failed:", tok.get("error"), file=sys.stderr)
        return 1
    save(AUTH, {"refresh_token": tok["refresh_token"]})
    print("session ok for", minecraft_from_ms(tok["access_token"]))
    return 0


if __name__ == "__main__":
    sys.exit({"login": login, "token": token}[sys.argv[1]]())
