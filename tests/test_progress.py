import io
import time

from activy_checker.progress import FRAMES, Spinner


class TTY(io.StringIO):
    def isatty(self):
        return True


def test_disabled_when_stream_is_not_a_terminal():
    out = io.StringIO()
    with Spinner("Working", stream=out) as sp:
        sp.update("Still working")
    assert out.getvalue() == ""


def test_animates_and_clears_line_on_a_terminal():
    out = TTY()
    with Spinner("Working", stream=out, interval=0.01) as sp:
        time.sleep(0.05)
        sp.update("Page 3")
        time.sleep(0.05)
    text = out.getvalue()
    assert "Working" in text and "Page 3" in text
    assert any(f in text for f in FRAMES)
    assert text.endswith("\r")  # line cleared at the end


def test_final_message_printed_after_stop():
    out = TTY()
    sp = Spinner("Working", stream=out, interval=0.01).start()
    sp.stop(final="Done: 3 activities")
    assert out.getvalue().endswith("Done: 3 activities\n")


def test_stop_is_idempotent_and_safe_before_start():
    sp = Spinner("x", stream=TTY())
    sp.stop()
    sp.start()
    sp.stop()
    sp.stop()


def test_exception_inside_block_still_stops_thread():
    out = TTY()
    sp = Spinner("Working", stream=out, interval=0.01)
    try:
        with sp:
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert sp._thread is None
