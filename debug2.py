import core.subtitle_engine as se
orig = se.generate_ass_subtitle
def wrap(*args, **kwargs):
    print("Calling with correct_text=", kwargs.get('correct_text'))
    return orig(*args, **kwargs)
se.generate_ass_subtitle = wrap
