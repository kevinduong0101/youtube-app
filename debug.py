import core.subtitle_engine as se
orig = se.format_ass_time
def wrap(t):
    return orig(t)
se.format_ass_time = wrap
