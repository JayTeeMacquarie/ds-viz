from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, BinaryIO

if TYPE_CHECKING:
    from server import Server

file = "ds-config2-ff.txt"


class Job:
    def __init__(self, jid: int, cores: int):
        self.jid = jid
        self.cores = cores
        self.schd = None
        self.start = None
        self.end = None


def get_jobs(servers: Dict[str, Dict[int, Server]]) -> List[Job]:
    jobs = []

    with open(file, "rb") as f:
        while True:
            line = f.readline()

            if b"JOBN" in line:
                f.seek(-len(line), 1)
                job = make_job(f, servers)
                jobs.append(job)

            if not line:
                break

    return jobs


def make_job(f: BinaryIO, servers: Dict[str, Dict[int, Server]]) -> Job:
    msg = f.readline().decode("utf-8").split()
    jid, cores = int(msg[3]), int(msg[5])

    while True:
        line = f.readline()

        if b"SCHD" in line:
            msg = line.decode("utf-8").split()
            server = servers[msg[3]][int(msg[4])]
            job = Job(int(msg[2]), cores)
            server.jobs.append(job)

            return job

        if not line:
            break


def job_list_to_dict(jobs: List[Job]) -> Dict[int, Job]:
    j_dict: Dict[int, Job] = {}

    for j in jobs:
        j_dict[j.jid] = j

    return j_dict
