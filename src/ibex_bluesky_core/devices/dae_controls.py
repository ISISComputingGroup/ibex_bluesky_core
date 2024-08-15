from ophyd_async.core import SignalX, StandardReadable
from ophyd_async.epics.signal import epics_signal_x


class DaeControls(StandardReadable):
    def __init__(self, dae_prefix, name=""):
        self.begin_run: SignalX = epics_signal_x(f"{dae_prefix}BEGINRUN")
        self.begin_run_ex: SignalX = epics_signal_x(f"{dae_prefix}BEGINRUNEX")

        self.end_run: SignalX = epics_signal_x(f"{dae_prefix}ENDRUN")
        self.pause_run: SignalX = epics_signal_x(f"{dae_prefix}PAUSERUN")
        self.resume_run: SignalX = epics_signal_x(f"{dae_prefix}RESUMERUN")
        self.abort_run: SignalX = epics_signal_x(f"{dae_prefix}ABORTRUN")
        self.recover_run: SignalX = epics_signal_x(f"{dae_prefix}RECOVERRUN")
        self.save_run: SignalX = epics_signal_x(f"{dae_prefix}SAVERUN")

        super().__init__(name=name)
