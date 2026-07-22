import core.subtitle_engine as se
orig = se.generate_ass_subtitle
def wrap(*args, **kwargs):
    # I want to modify generate_ass_subtitle temporarily
    pass
