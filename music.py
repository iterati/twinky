"""twinky's beat clock, kept from the music messages the page sends about 30 times a second as it
listens: each says where the beat was at a time on the Mac's clock, which twinky shares."""
from dataclasses import dataclass, replace

# How long after the last message the links let go, in seconds
LET_GO = 1.0

@dataclass(frozen=True)
class Sound:
    """What the page heard at a time: the fields of its music message."""
    time: float  # on the Mac's clock, seconds since 1970, as time.time() gives
    bpm: float  # 0 until the page finds a tempo
    beat: float  # beats counted at time, the fraction its phase: 0 on a beat
    bar: int  # whole bars counted at time, 4 beats a bar
    confidence: float  # how well the sound's onsets land on the beat, 0 to 1
    low: float  # the bands, each 0 to 1 of its own range over the last 10 s
    mid: float
    high: float
    tone: float  # 0 dark to 1 light
    drive: float  # 0 groove to 1 drive

class BeatClock:
    """The last message heard, extrapolated at its bpm to any time until the links let go."""
    def __init__(self):
        self.heard: Sound | None = None

    def hear(self, message: dict):
        """Takes a music message, from the server's thread."""
        self.heard = Sound(**message)

    def at(self, t: float, latency: float=0.0) -> Sound | None:
        """The sound at t, its beat extrapolated from the last message: with a latency, as it was that
        many seconds earlier (later, if negative), so the lights line up with what the room hears.
        None once no message has come for LET_GO seconds."""
        heard = self.heard
        if heard is None or t - heard.time > LET_GO:
            return None
        beat = heard.beat + ((t - latency - heard.time) * heard.bpm / 60)
        return replace(heard, time=t, beat=beat, bar=int(beat // 4))
