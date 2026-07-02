from constant import PatternContext
from tool import AteSession

def RW_DQ_DQS_DELAY(session:AteSession, rl, wl):
    session.command("R").delay = rl
    session.command("RDQSL").delay = rl
    session.command("RDQSH").delay = rl

    session.command("W").delay = wl
    session.command("WDQSH").delay = wl
    session.command("WDQSL").delay = wl

