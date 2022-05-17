import re
import sys
from collections import OrderedDict
from itertools import chain
from typing import List, Dict, BinaryIO, Union
from xml.etree.ElementTree import parse

from file_read_backwards import FileReadBackwards

from job import Job, get_jobs
from server_failure import ServerFailure, get_failures, get_failures_from_resources
from server_state import ServerState as State


class Server:
    end_time = None  # type: int

    def __init__(self, type_: str, sid: int, cores: int, memory: int, disk: int,
                 states: Dict[int, State] = None, jobs: List[Job] = None,
                 failures: List[ServerFailure] = None):
        self.type_ = type_
        self.sid = sid
        self.cores = cores
        self.memory = memory
        self.disk = disk
        self.states = states if states else {0: State.inactive}
        self.jobs = jobs if jobs else []
        self.failures = failures if failures else []

    def __str__(self):
        return "{} {}".format(self.type_, self.sid)

    def get_server_at(self, t: int) -> "Server":
        jobs = list(filter(lambda j: j.is_running_at(t), self.jobs))
        cores = self.cores - sum(j.cores for j in jobs)
        memory = self.memory - sum(j.memory for j in jobs)
        disk = self.disk - sum(j.disk for j in jobs)
        states = {0: self.get_state_at(t)}

        return Server(self.type_, self.sid, cores, memory, disk, states, jobs)

    def get_state_at(self, t: int) -> State:
        best = None
        diff = sys.maxsize

        for time, stat in self.states.items():
            d = t - time

            if d == 0:
                return stat
            elif 0 < d < diff:
                best = stat
                diff = d
        return best

    def count_failures_at(self, t: int) -> int:
        res = 0

        for time in sorted(self.states):
            if time > t:
                break
            if self.states[time] == State.unavailable:
                res += 1
        return res

    def print_server_at(self, t: int) -> str:
        cur = self.get_server_at(t)

        queued_jobs = list(filter(lambda j: j.is_queued_at(t), self.jobs))
        completed_jobs = list(filter(lambda j: j.is_completed_at(t), self.jobs))
        failed_jobs = list(filter(lambda j: j.is_failed_at(t), self.jobs))

        return (
                "{} {}: {},  ".format(self.type_, self.sid, cur.states[0].name) +
                "cores: {} ({}),  ".format(cur.cores, self.cores) +
                "memory: {} ({}),\n".format(cur.memory, self.memory) +
                "disk: {} ({}),  ".format(cur.disk, self.disk) +
                "running jobs: {},  ".format(len(cur.jobs)) +
                "queued jobs: {},\n".format(len(queued_jobs)) +
                "completed jobs: {},  ".format(len(completed_jobs)) +
                "failed jobs: {},  ".format(len(failed_jobs)) +
                "server failures: {}".format(self.count_failures_at(t))
        )

    def print_job_info(self, t: int) -> str:
        running_jobs = [j.jid for j in self.get_server_at(t).jobs]
        queued_jobs = [j.jid for j in filter(lambda j: j.is_queued_at(t), self.jobs)]
        completed_jobs = [j.jid for j in filter(lambda j: j.is_completed_at(t), self.jobs)]
        failed_jobs = [j.jid for j in filter(lambda j: j.is_failed_at(t), self.jobs)]

        return (
                "RUNNING: {}\n".format(running_jobs) +
                "QUEUED: {}\n".format(queued_jobs) +
                "COMPLETED: {}\n".format(completed_jobs) +
                "FAILED: {}\n".format(failed_jobs)
        )

    def get_server_states(self, log: str) -> None:
        states = {0: State.inactive}  # type: Dict[int, State]

        with open(log, "r") as f:
            while True:
                line = f.readline()

                if not line:
                    break

                msg = line.split()

                if msg[0] == "t:":
                    time = int(msg[1])

                    s_info = line.split('#')[1].split()  # Make everything left of '#' into a list
                    sid = int(s_info[0])
                    type_ = s_info[3]

                    if type_ == self.type_ and sid == self.sid:
                        if "(booting)" in msg:
                            states[time] = State.booting
                        elif "RUNNING" in msg and states[max(states)] is not State.active:
                            states[time] = State.active
                        elif "COMPLETED" in msg and time != Server.end_time and len(
                                list(filter(lambda j: j.is_running_at(time + 1), self.jobs))) == 0:
                            states[time + 1] = State.idle

        for f in self.failures:
            states[f.fail] = State.unavailable

            if f.recover != Server.end_time:
                states[f.recover] = State.inactive

        self.states = states


def get_servers_from_system(log: str, system: str, resource_failures: str = None) -> \
        "OrderedDict[str, OrderedDict[int, Server]]":
    Server.end_time = simulation_end_time(log)
    servers = OrderedDict()  # type: OrderedDict[str, OrderedDict[int, Server]]

    for s in parse(system).iter("server"):
        type_ = s.attrib["type"]
        servers[type_] = OrderedDict()  # type: OrderedDict[int, Server]

        for i in range(int(s.attrib["limit"])):
            servers[type_][i] = Server(
                type_, i, int(s.attrib["cores"]), int(s.attrib["memory"]), int(s.attrib["disk"]))

    get_jobs(log, servers)

    if resource_failures:
        get_failures_from_resources(resource_failures, servers)

    for s in traverse_servers(servers):
        s.get_server_states(log)

    return servers


def get_servers(log: str) -> List[Server]:
    with open(log, "rb") as f:
        while True:
            line = f.readline()

            if b"RESC All" in line:
                servers = make_servers(f)
                s_dict = server_list_to_dict(servers)
                get_jobs(log, s_dict)
                get_failures(log, s_dict, Server.end_time)

                return servers

            if not line:
                break


def make_servers(f: BinaryIO) -> List[Server]:
    servers = []

    while True:
        line = f.readline()

        if not line:
            break

        msg = line.decode("utf-8").split()

        if "." in msg:
            break

        if not any([i in msg for i in ["OK", "DATA"]]):
            servers.append(Server(msg[1], int(msg[2]), int(msg[5]), int(msg[6]), int(msg[7])))

    return servers


def get_results(log: str) -> str:
    with FileReadBackwards(log, encoding="utf-8") as f:
        results = []  # type: List[str]

        while True:
            line = f.readline().replace("\r\n", "\n")
            results.append(line[2:])  # Remove '#'s

            if line == "SENT QUIT\n":
                # Remove last two lines and reverse the list
                return ''.join(reversed(results[:-2]))

            if not line:
                sys.exit("ERROR: Insufficient information in log file. "
                         "Please use '-v brief' or '-v all' when creating a log with ds-server.")


def simulation_end_time(log: str) -> int:
    re_time = re.compile(r".*actual simulation end time: (\d+).*")

    with FileReadBackwards(log, encoding="utf-8") as f:
        for line in f:
            time = re_time.match(line)

            if time is not None:
                return int(time.group(1))
    sys.exit("ERROR: simulation end time could not be retrieved")


def print_servers_at(servers: List[Server], t: int) -> str:
    curs = [s.get_server_at(t) for s in servers]

    s_inactive = list(filter(lambda s: s.states[0] == State.inactive, curs))
    s_booting = list(filter(lambda s: s.states[0] == State.booting, curs))
    s_idle = list(filter(lambda s: s.states[0] == State.idle, curs))
    s_active = list(filter(lambda s: s.states[0] == State.active, curs))
    s_unavailable = list(filter(lambda s: s.states[0] == State.unavailable, curs))
    s_failures = sum(s.count_failures_at(t) for s in servers)

    j_running = [j for s in curs for j in s.jobs]
    j_queued = list(chain.from_iterable(filter(lambda job: job.is_queued_at(t), s.jobs) for s in servers))
    j_completed = list(chain.from_iterable(filter(lambda job: job.is_completed_at(t), s.jobs) for s in servers))
    j_failed = list(chain.from_iterable(filter(lambda job: job.is_failed_at(t), s.jobs) for s in servers))

    return (
            "SERVERS: inactive: {},  ".format(len(s_inactive)) +
            "booting: {},  ".format(len(s_booting)) +
            "idle: {},  ".format(len(s_idle)) +
            "active: {},\n".format(len(s_active)) +
            "  unavailable: {} ({})\n".format(len(s_unavailable), s_failures) +
            "JOBS: running: {},  ".format(len(j_running)) +
            "queued: {},  ".format(len(j_queued)) +
            "completed: {},  ".format(len(j_completed)) +
            "failed: {}".format(len(j_failed))
    )


def server_list_to_dict(servers: List[Server]) -> "OrderedDict[str, OrderedDict[int, Server]]":
    s_dict = OrderedDict()

    for s in servers:
        if s.type_ not in s_dict:
            s_dict[s.type_] = OrderedDict()

        s_dict[s.type_][s.sid] = s

    return s_dict


# https://stackoverflow.com/a/17014386/8031185
def traverse_servers(item: "Union[OrderedDict[str, OrderedDict[int, Server]], OrderedDict[int, Server], Server]") \
        -> "Union[OrderedDict[str, OrderedDict[int, Server]], OrderedDict[int, Server], Server]":
    try:
        for i in item:
            for k in traverse_servers(item[i]):
                yield k
    except TypeError:
        yield item
