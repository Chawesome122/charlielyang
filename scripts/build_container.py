"""Build with the existing public-network proxy route and optional supplied CA.

Does not extract credentials, disable TLS, alter network policy or print proxy
values. The add-host entry preserves the existing proxy's DNS resolution inside
Docker, where the cloud machine's internal DNS alias is otherwise unavailable.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument("--target",default="research")
    parser.add_argument("--tag",default="weaponized-research")
    args=parser.parse_args()
    os.chdir(ROOT)
    env=dict(os.environ)
    env["DOCKER_CONFIG"]=str(ROOT/".cache/docker")
    command=["docker","build","--target",args.target,"-t",args.tag]
    proxies={}
    hosts=set()
    for scheme in ["http","https"]:
        value=env.get(f"{scheme}_proxy") or env.get(f"{scheme.upper()}_PROXY")
        if value:
            proxies[scheme]=True
            command += ["--build-arg",f"{scheme}_proxy={value}"]
            host=urlsplit(value).hostname
            if host and host not in hosts:
                address=socket.gethostbyname(host)
                command += ["--add-host",f"{host}:{address}"]
                hosts.add(host)
    cert=env.get("CODEX_PROXY_CERT")
    supplied_ca=bool(cert and Path(cert).is_file())
    if supplied_ca:
        command += ["--secret",f"id=proxy_ca,src={cert}"]
    command += ["."]
    logpath=ROOT/"outputs/diagnostics/docker_build.log"
    logpath.parent.mkdir(parents=True,exist_ok=True)
    with logpath.open("w") as log:
        result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
    report=dict(exit_code=result.returncode,tag=args.tag,target=args.target,
                existing_proxy_forwarded=proxies,existing_proxy_dns_mapping_used=bool(hosts),
                platform_public_ca_used=supplied_ca,tls_verification_disabled=False,log=str(logpath.relative_to(ROOT)))
    if result.returncode==0:
        inspect=subprocess.run(["docker","image","inspect",args.tag,"--format","{{.Id}}"],env=env,capture_output=True,text=True,check=True)
        report["image_id"]=inspect.stdout.strip()
    (ROOT/"outputs/diagnostics/container_build.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    return result.returncode


if __name__=="__main__":raise SystemExit(main())
